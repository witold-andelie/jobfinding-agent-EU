"""Job store protocol + in-memory implementation, deduping on (source, external_id)."""

from __future__ import annotations

from typing import Protocol

from job_agent.models.job import Job


def dedupe_jobs(jobs: list[Job]) -> list[Job]:
    """Drop duplicates on ``(source, external_id)``, keeping first occurrence.

    Same dedupe key the reference enforces with a Supabase unique constraint —
    applied in-process so it holds regardless of backend.
    """
    seen: set[tuple[str, str]] = set()
    out: list[Job] = []
    for job in jobs:
        key = (job.source, job.external_id)
        if key in seen:
            continue
        seen.add(key)
        out.append(job)
    return out


class JobStore(Protocol):
    def upsert_jobs(self, jobs: list[Job]) -> int:
        """Persist jobs (deduped on (source, external_id)); return count stored."""
        ...


class InMemoryJobStore:
    """Dict-backed store keyed on (source, external_id)."""

    def __init__(self) -> None:
        self._jobs: dict[tuple[str, str], Job] = {}

    def upsert_jobs(self, jobs: list[Job]) -> int:
        for job in jobs:
            self._jobs[(job.source, job.external_id)] = job
        return len(jobs)

    def all(self) -> list[Job]:
        return list(self._jobs.values())
