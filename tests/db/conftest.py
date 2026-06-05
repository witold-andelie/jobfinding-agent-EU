"""A fake Supabase client that records the fluent calls made against it (no network)."""

from __future__ import annotations

from typing import Any

import pytest


class _Query:
    def __init__(self, log: list[dict[str, Any]], table: str) -> None:
        self._log = log
        self._record: dict[str, Any] = {"table": table, "op": None, "payload": None,
                                        "on_conflict": None, "filters": []}

    def insert(self, data: Any) -> "_Query":
        self._record.update(op="insert", payload=data)
        return self

    def upsert(self, data: Any, on_conflict: str | None = None) -> "_Query":
        self._record.update(op="upsert", payload=data, on_conflict=on_conflict)
        return self

    def update(self, data: Any) -> "_Query":
        self._record.update(op="update", payload=data)
        return self

    def eq(self, column: str, value: Any) -> "_Query":
        self._record["filters"].append((column, value))
        return self

    def execute(self) -> dict[str, Any]:
        self._log.append(self._record)
        return self._record


class FakeSupabase:
    def __init__(self) -> None:
        self.calls: list[dict[str, Any]] = []

    def table(self, name: str) -> _Query:
        return _Query(self.calls, name)


@pytest.fixture
def fake_supabase() -> FakeSupabase:
    return FakeSupabase()
