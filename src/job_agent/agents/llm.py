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

# DeepSeek deepseek-chat list price (USD per token); approximate, adjust as needed.
_USD_PER_PROMPT_TOKEN = 0.27 / 1_000_000
_USD_PER_COMPLETION_TOKEN = 1.10 / 1_000_000


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
        if client is not None:
            self._client = client
            return
        _settings.require_llm_credentials()
        from openai import OpenAI  # lazy import — keeps the package import-safe offline

        self._client = OpenAI(
            api_key=_settings.llm_api_key,
            base_url=_settings.llm_base_url or "https://api.deepseek.com",
        )

    def ask(self, prompt: str) -> str:
        """Single-turn completion; returns the assistant text and records cost."""
        started = time.perf_counter()
        resp = self._client.chat.completions.create(
            model=self._model,
            messages=[{"role": "user", "content": prompt}],
            temperature=0,
        )
        duration_ms = int((time.perf_counter() - started) * 1000)
        content = resp.choices[0].message.content or ""

        if self._obs is not None:
            usage = getattr(resp, "usage", None)
            prompt_tokens = getattr(usage, "prompt_tokens", None)
            completion_tokens = getattr(usage, "completion_tokens", None)
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
