"""Supabase-backed JobStore — a drop-in for InMemoryJobStore.

Implements the same ``JobStore`` protocol (upsert deduped on ``(source,
external_id)``) against the ``jobs`` table, so Scout is unchanged: pass this store
instead of the in-memory one. Enums are serialised to their string values to match
the SQL text columns.
"""

from __future__ import annotations

from typing import Any

from job_agent.db.client import SupabaseClient
from job_agent.models.application import Application
from job_agent.models.job import Job
from job_agent.persistence.store import dedupe_jobs


def _row(job: Job) -> dict[str, Any]:
    return {
        "source": job.source,
        "external_id": job.external_id,
        "title": job.title,
        "company": job.company,
        "country": job.country,
        "city": job.city,
        "track": job.track.value,
        "source_type": job.source_type,
        "languages_required": job.languages_required,
        "salary_eur": job.salary_eur,
        "description": job.description,
        "url": job.url,
        "visa_signal": job.visa_signal.value,
        "employment_type": job.employment_type.value,
    }


class SupabaseJobStore:
    def __init__(self, db: SupabaseClient) -> None:
        self._db = db

    def upsert_jobs(self, jobs: list[Job]) -> int:
        rows = [_row(j) for j in dedupe_jobs(jobs)]
        if rows:
            self._db.raw.table("jobs").upsert(rows, on_conflict="source,external_id").execute()
        return len(rows)


class SupabaseApplicationStore:
    """Drop-in for ``InMemoryApplicationStore`` against the ``applications`` table.

    ``Application.model_dump(mode="json")`` matches the table columns field-for-field
    (id is the app UUID, datetimes as ISO strings, history as JSON), so save is a
    plain upsert on ``id`` and read reconstructs the model directly.
    """

    def __init__(self, db: SupabaseClient) -> None:
        self._db = db

    def save(self, application: Application) -> None:
        self._db.raw.table("applications").upsert(
            application.model_dump(mode="json"), on_conflict="id"
        ).execute()

    def get(self, application_id: str) -> Application | None:
        resp = self._db.raw.table("applications").select("*").eq("id", application_id).execute()
        rows = resp.data or []
        return Application(**rows[0]) if rows else None

    def all(self) -> list[Application]:
        resp = self._db.raw.table("applications").select("*").execute()
        return [Application(**row) for row in (resp.data or [])]
