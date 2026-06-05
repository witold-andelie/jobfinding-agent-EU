"""Application store protocol + in-memory implementation."""

from __future__ import annotations

from typing import Protocol

from job_agent.models.application import Application


class ApplicationStore(Protocol):
    def save(self, application: Application) -> None: ...

    def get(self, application_id: str) -> Application | None: ...

    def all(self) -> list[Application]: ...


class InMemoryApplicationStore:
    def __init__(self) -> None:
        self._apps: dict[str, Application] = {}

    def save(self, application: Application) -> None:
        self._apps[application.id] = application

    def get(self, application_id: str) -> Application | None:
        return self._apps.get(application_id)

    def all(self) -> list[Application]:
        return list(self._apps.values())
