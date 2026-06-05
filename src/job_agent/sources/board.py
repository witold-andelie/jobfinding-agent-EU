"""Board-source abstraction (Layer 1 aggregators + Track B intl-org).

Unlike ATS adapters (company-keyed, fetched via the header-less ``HttpGet``), board
sources query a portal for many employers at once and may need auth headers (e.g.
Arbeitsagentur's API key, EURES credentials). So they share a slightly richer
transport seam, ``HttpJson`` — still a single injected callable, so everything
stays unit-testable offline with fixtures.
"""

from __future__ import annotations

from collections.abc import Mapping
from typing import Callable, Protocol

from job_agent.discovery.base import DiscoveryQuery
from job_agent.models.job import Job

# (url, headers) -> response body text. Headers default to none.
HttpJson = Callable[[str, Mapping[str, str] | None], str]


class BoardSource(Protocol):
    """A portal queried for jobs across many employers."""

    name: str

    def fetch(self, query: DiscoveryQuery) -> list[Job]: ...
