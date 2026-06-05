"""Observability store protocol + in-memory implementation."""

from __future__ import annotations

from datetime import datetime, timezone
from typing import Protocol

from job_agent.observability.run_context import RunContext


class ObservabilityStore(Protocol):
    """Mirrors the reference project's ObservabilityStore surface."""

    def insert_run(self, ctx: RunContext) -> None: ...

    def finish_run(self, run_id: str, status: str, error_message: str | None = None) -> None: ...

    def insert_llm_event(
        self,
        *,
        run_id: str | None,
        prompt_snippet: str,
        response_snippet: str,
        prompt_tokens: int | None,
        completion_tokens: int | None,
        duration_ms: int,
        cost_usd: float | None,
    ) -> None: ...


class InMemoryObservability:
    """Records runs + LLM events in lists — for offline runs, tests, and the dashboard."""

    def __init__(self) -> None:
        self.runs: list[dict[str, object]] = []
        self.llm_events: list[dict[str, object]] = []

    def insert_run(self, ctx: RunContext) -> None:
        self.runs.append(
            {
                "run_id": ctx.run_id,
                "agent_name": ctx.agent_name,
                "started_at": ctx.started_at,
                "status": "running",
                "finished_at": None,
                "error_message": None,
            }
        )

    def finish_run(self, run_id: str, status: str, error_message: str | None = None) -> None:
        for run in self.runs:
            if run["run_id"] == run_id:
                run["status"] = status
                run["finished_at"] = datetime.now(timezone.utc)
                run["error_message"] = error_message
                return

    def insert_llm_event(
        self,
        *,
        run_id: str | None,
        prompt_snippet: str,
        response_snippet: str,
        prompt_tokens: int | None,
        completion_tokens: int | None,
        duration_ms: int,
        cost_usd: float | None,
    ) -> None:
        self.llm_events.append(
            {
                "run_id": run_id,
                "prompt_snippet": prompt_snippet,
                "response_snippet": response_snippet,
                "prompt_tokens": prompt_tokens,
                "completion_tokens": completion_tokens,
                "duration_ms": duration_ms,
                "cost_usd": cost_usd,
            }
        )

    def total_cost_usd(self) -> float:
        return sum(float(e["cost_usd"] or 0.0) for e in self.llm_events)
