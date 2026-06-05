"""Tracker — lifecycle transitions, applied_at, follow-up reminders (offline)."""

from datetime import timedelta

import pytest

from job_agent.models.application import ApplicationStatus, utcnow
from job_agent.models.job import Job
from job_agent.tracker import InvalidTransition, Tracker, can_transition

_JOB = Job(source="personio", external_id="1", title="Junior PA Officer", company="Rhône SA",
           country="CH")


def test_create_starts_new_with_history() -> None:
    t = Tracker()
    app = t.create(_JOB, candidate_ref="mei", cover_letter="Dear...")
    assert app.status is ApplicationStatus.new
    assert app.company == "Rhône SA" and app.cover_letter == "Dear..."
    assert app.history[0]["status"] == "new"


def test_happy_path_applied_sets_timestamp() -> None:
    t = Tracker()
    app = t.create(_JOB, "mei")
    now = utcnow()
    t.advance(app.id, ApplicationStatus.applied, now=now)
    t.advance(app.id, ApplicationStatus.interview)
    updated = t.applications("mei")[0]
    assert updated.status is ApplicationStatus.interview
    assert updated.applied_at == now  # set on the applied transition
    assert [h["status"] for h in updated.history] == ["new", "applied", "interview"]


def test_invalid_transition_is_rejected() -> None:
    t = Tracker()
    app = t.create(_JOB, "mei")
    with pytest.raises(InvalidTransition):
        t.advance(app.id, ApplicationStatus.offer)  # can't jump new → offer
    assert not can_transition(ApplicationStatus.rejected, ApplicationStatus.applied)  # terminal


def test_due_followups_after_n_days() -> None:
    t = Tracker()
    old = t.create(_JOB, "mei")
    fresh = t.create(_JOB, "mei")
    long_ago = utcnow() - timedelta(days=10)
    t.advance(old.id, ApplicationStatus.applied, now=long_ago)
    t.advance(fresh.id, ApplicationStatus.applied)  # applied just now

    due = t.due_followups(days=7)
    assert [a.id for a in due] == [old.id]  # only the 10-day-old one

    t.mark_followed_up(old.id)
    assert t.due_followups(days=7) == []  # cleared after follow-up


def test_advance_unknown_id_raises() -> None:
    with pytest.raises(KeyError):
        Tracker().advance("nope", ApplicationStatus.applied)
