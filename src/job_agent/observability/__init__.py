"""Observability — run tracking. Offline-capable.

The reference project writes runs to Supabase (``agent_runs``/``llm_events``). We
keep that as the ``ObservabilityStore`` protocol and ship an in-memory
implementation so agents are fully observable in tests without a database; the
Supabase-backed store is a drop-in adapter added with the persistence layer.
"""

from job_agent.observability.run_context import RunContext, get_current_run, start_run
from job_agent.observability.store import InMemoryObservability, ObservabilityStore

__all__ = [
    "InMemoryObservability",
    "ObservabilityStore",
    "RunContext",
    "get_current_run",
    "start_run",
]
