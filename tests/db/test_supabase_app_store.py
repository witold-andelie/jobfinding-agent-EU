"""SupabaseApplicationStore — round-trip via a stateful fake Supabase table."""

from job_agent.db.client import SupabaseClient
from job_agent.models.application import ApplicationStatus
from job_agent.models.job import Job
from job_agent.persistence.supabase import SupabaseApplicationStore
from job_agent.tracker import Tracker

_JOB = Job(source="personio", external_id="1", title="Junior PA", company="Rhône SA", country="CH")


class _StatefulTable:
    """Minimal stand-in for a Supabase table: upsert / select / eq / execute."""

    def __init__(self, rows: dict[str, dict]) -> None:
        self._rows = rows
        self._filter: tuple[str, object] | None = None

    def upsert(self, row, on_conflict=None):
        self._rows[row["id"]] = row
        return self

    def select(self, _cols):
        return self

    def eq(self, col, val):
        self._filter = (col, val)
        return self

    def execute(self):
        data = list(self._rows.values())
        if self._filter:
            col, val = self._filter
            data = [r for r in data if r.get(col) == val]
        return type("Resp", (), {"data": data})()


class _FakeDB:
    def __init__(self) -> None:
        self.rows: dict[str, dict] = {}

    def table(self, name):
        assert name == "applications"
        return _StatefulTable(self.rows)


def test_application_store_roundtrips_through_tracker() -> None:
    store = SupabaseApplicationStore(SupabaseClient(client=_FakeDB()))
    tracker = Tracker(store)

    app = tracker.create(_JOB, candidate_ref="mei", cover_letter="Dear...")
    tracker.advance(app.id, ApplicationStatus.applied)

    # Read back through a fresh Tracker on the same store → state persisted.
    reloaded = Tracker(store).applications("mei")
    assert len(reloaded) == 1
    got = reloaded[0]
    assert got.id == app.id and got.status is ApplicationStatus.applied
    assert got.cover_letter == "Dear..." and got.applied_at is not None
    assert [h["status"] for h in got.history] == ["new", "applied"]
