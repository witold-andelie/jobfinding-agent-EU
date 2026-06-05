"""Persistence seam.

The reference project dedupes jobs on ``(source, external_id)`` via a Supabase
unique constraint. We keep that contract as the ``JobStore`` protocol and ship an
in-memory store for offline runs/tests; the Supabase-backed store (adapting the
reference's ``db/client.py`` + ``001_init.sql``) is a drop-in added later.
"""

from job_agent.persistence.store import InMemoryJobStore, JobStore, dedupe_jobs

__all__ = ["InMemoryJobStore", "JobStore", "dedupe_jobs"]
