"""Supabase-backed ObservabilityStore — a drop-in for InMemoryObservability.

Writes runs to ``agent_runs`` and per-call cost to ``llm_events`` (adapted from the
reference project's ObservabilityStore). Same protocol, so LLMClient/Scout are
unchanged.
"""

from __future__ import annotations

from datetime import datetime, timezone

from job_agent.db.client import SupabaseClient
from job_agent.observability.run_context import RunContext


class SupabaseObservability:
    def __init__(self, db: SupabaseClient) -> None:
        self._db = db

    def insert_run(self, ctx: RunContext) -> None:
        self._db.raw.table("agent_runs").insert(
            {
                "run_id": ctx.run_id,
                "agent_name": ctx.agent_name,
                "started_at": ctx.started_at.isoformat(),
                "status": "running",
            }
        ).execute()

    def finish_run(self, run_id: str, status: str, error_message: str | None = None) -> None:
        self._db.raw.table("agent_runs").update(
            {
                "status": status,
                "finished_at": datetime.now(timezone.utc).isoformat(),
                "error_message": error_message,
            }
        ).eq("run_id", run_id).execute()

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
        self._db.raw.table("llm_events").insert(
            {
                "run_id": run_id,
                "prompt_snippet": prompt_snippet,
                "response_snippet": response_snippet,
                "prompt_tokens": prompt_tokens,
                "completion_tokens": completion_tokens,
                "cost_usd": cost_usd,
                "duration_ms": duration_ms,
            }
        ).execute()
