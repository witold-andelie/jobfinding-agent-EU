"""Tracker — application lifecycle state machine + follow-up reminders.

The fourth agent: once the Writer has prepared an application, the Tracker records
it, enforces valid status transitions, and surfaces applications due a follow-up.
Pure domain logic over an injectable ``ApplicationStore`` → fully offline-testable.
"""

from job_agent.tracker.state_machine import (
    ALLOWED_TRANSITIONS,
    TERMINAL,
    InvalidTransition,
    assert_transition,
    can_transition,
)
from job_agent.tracker.store import ApplicationStore, InMemoryApplicationStore
from job_agent.tracker.tracker import Tracker

__all__ = [
    "ALLOWED_TRANSITIONS",
    "ApplicationStore",
    "InMemoryApplicationStore",
    "InvalidTransition",
    "TERMINAL",
    "Tracker",
    "assert_transition",
    "can_transition",
]
