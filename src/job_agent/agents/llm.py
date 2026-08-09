"""LLM client — DeepSeek via its OpenAI-compatible API.

DeepSeek speaks the OpenAI protocol, so we use the ``openai`` SDK pointed at
``https://api.deepseek.com``. Mirrors the reference project's ``BaseAgent``:
dependency-injection seam (``client=`` in tests), credential guard on the live
path, and the SDK import is lazy so importing this module never requires ``openai``
and offline tests stay dependency-free.

When an ``ObservabilityStore`` is injected, every call records an ``llm_event``
(token counts + estimated cost) against the active run — the cost-tracking the
reference did for GWDG, here priced for DeepSeek.

Use ``LLMClient().ask`` as the callable seam for ``PromptedVisaSignalLLM`` and any
later LLM-backed agent (Matcher gap analysis, Writer).
"""

from __future__ import annotations

import time
from typing import Any

from job_agent.config import Settings, get_settings
from job_agent.observability import ObservabilityStore, get_current_run

# DeepSeek-V4-Flash list price (USD per token); provider/model costs may differ.
_USD_PER_PROMPT_TOKEN = 0.14 / 1_000_000  # cache-miss input price
_USD_PER_COMPLETION_TOKEN = 0.28 / 1_000_000


def _estimate_cost(prompt_tokens: int | None, completion_tokens: int | None) -> float | None:
    if prompt_tokens is None or completion_tokens is None:
        return None
    return prompt_tokens * _USD_PER_PROMPT_TOKEN + completion_tokens * _USD_PER_COMPLETION_TOKEN


class LLMClient:
    def __init__(
        self,
        settings: Settings | None = None,
        client: Any | None = None,
        obs: ObservabilityStore | None = None,
    ) -> None:
        _settings = settings if settings is not None else get_settings()
        self._model = _settings.llm_model
        self._obs = obs
        self._use_responses = (
            _settings.llm_api_mode.lower() == "responses"
            or _settings.llm_base_url.rstrip("/").endswith("/responses")
        )
        if client is not None:
            self._client = client
            # Keep injected OpenAI-shaped fakes backward-compatible with the
            # legacy chat-completions seam, even when the local .env selects Responses.
            if self._use_responses and not hasattr(client, "responses"):
                self._use_responses = False
            return
        _settings.require_llm_credentials()
        from openai import OpenAI  # lazy import — keeps the package import-safe offline

        base_url = _settings.llm_base_url.rstrip("/")
        if self._use_responses:
            base_url = base_url.removesuffix("/responses")
        self._client = OpenAI(
            api_key=_settings.llm_api_key,
            base_url=base_url or "https://api.deepseek.com",
        )

    def ask(self, prompt: str) -> str:
        """Single-turn completion; returns the assistant text and records cost."""
        started = time.perf_counter()
        if self._use_responses:
            resp = self._client.responses.create(model=self._model, input=prompt)
        else:
            resp = self._client.chat.completions.create(
                model=self._model,
                messages=[{"role": "user", "content": prompt}],
                temperature=0,
            )
        duration_ms = int((time.perf_counter() - started) * 1000)
        if self._use_responses:
            content = getattr(resp, "output_text", "") or ""
        else:
            content = resp.choices[0].message.content or ""

        if self._obs is not None:
            usage = getattr(resp, "usage", None)
            prompt_tokens = getattr(usage, "input_tokens", None) or getattr(
                usage, "prompt_tokens", None
            )
            completion_tokens = getattr(usage, "output_tokens", None) or getattr(
                usage, "completion_tokens", None
            )
            run = get_current_run()
            self._obs.insert_llm_event(
                run_id=run.run_id if run else None,
                prompt_snippet=prompt[:200],
                response_snippet=content[:200],
                prompt_tokens=prompt_tokens,
                completion_tokens=completion_tokens,
                duration_ms=duration_ms,
                cost_usd=_estimate_cost(prompt_tokens, completion_tokens),
            )
        return content
