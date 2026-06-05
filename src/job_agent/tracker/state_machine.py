"""Application status state machine: new → applied → interview → offer/…"""

from __future__ import annotations

from job_agent.models.application import ApplicationStatus as S

ALLOWED_TRANSITIONS: dict[S, set[S]] = {
    S.new: {S.applied, S.withdrawn},
    S.applied: {S.interview, S.rejected, S.withdrawn},
    S.interview: {S.offer, S.rejected, S.withdrawn},
    S.offer: {S.accepted, S.rejected, S.withdrawn},
    S.accepted: set(),
    S.rejected: set(),
    S.withdrawn: set(),
}

TERMINAL: set[S] = {S.accepted, S.rejected, S.withdrawn}


class InvalidTransition(Exception):
    def __init__(self, frm: S, to: S) -> None:
        super().__init__(f"invalid application transition: {frm.value} → {to.value}")


def can_transition(frm: S, to: S) -> bool:
    return to in ALLOWED_TRANSITIONS.get(frm, set())


def assert_transition(frm: S, to: S) -> None:
    if not can_transition(frm, to):
        raise InvalidTransition(frm, to)
