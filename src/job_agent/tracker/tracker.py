"""Tracker agent — create applications, advance status, surface follow-ups."""

from __future__ import annotations

from datetime import datetime, timedelta

from job_agent.models.application import Application, ApplicationStatus, utcnow
from job_agent.models.job import Job
from job_agent.tracker.state_machine import assert_transition
from job_agent.tracker.store import ApplicationStore, InMemoryApplicationStore


class Tracker:
    def __init__(self, store: ApplicationStore | None = None) -> None:
        self._store: ApplicationStore = store or InMemoryApplicationStore()

    def create(self, job: Job, candidate_ref: str, cover_letter: str | None = None) -> Application:
        """Record a prepared (not yet sent) application for a job."""
        app = Application(
            job_source=job.source,
            job_external_id=job.external_id,
            job_title=job.title,
            company=job.company,
            candidate_ref=candidate_ref,
            cover_letter=cover_letter,
        )
        app.history.append({"status": app.status.value, "at": app.created_at.isoformat()})
        self._store.save(app)
        return app

    def advance(
        self, application_id: str, to_status: ApplicationStatus, *, now: datetime | None = None
    ) -> Application:
        """Move an application to a new status, enforcing the state machine."""
        now = now or utcnow()
        app = self._store.get(application_id)
        if app is None:
            raise KeyError(application_id)
        assert_transition(app.status, to_status)
        app.status = to_status
        if to_status is ApplicationStatus.applied and app.applied_at is None:
            app.applied_at = now
        app.history.append({"status": to_status.value, "at": now.isoformat()})
        self._store.save(app)
        return app

    def due_followups(self, *, now: datetime | None = None, days: int = 7) -> list[Application]:
        """Applications stuck in 'applied' for ≥ ``days`` with no follow-up yet."""
        now = now or utcnow()
        cutoff = now - timedelta(days=days)
        return [
            a
            for a in self._store.all()
            if a.status is ApplicationStatus.applied
            and a.applied_at is not None
            and a.applied_at <= cutoff
            and a.follow_up_at is None
        ]

    def mark_followed_up(self, application_id: str, *, now: datetime | None = None) -> Application:
        app = self._store.get(application_id)
        if app is None:
            raise KeyError(application_id)
        app.follow_up_at = now or utcnow()
        self._store.save(app)
        return app

    def applications(self, candidate_ref: str | None = None) -> list[Application]:
        apps = self._store.all()
        if candidate_ref is not None:
            apps = [a for a in apps if a.candidate_ref == candidate_ref]
        return sorted(apps, key=lambda a: a.created_at, reverse=True)
