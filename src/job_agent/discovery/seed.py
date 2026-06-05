"""Seed-list discovery — curated companies with known ATS handles.

Highest-precision route: hand-maintained or client-supplied lists (e.g. "Czech IT
SMEs"). Returns only the companies matching the query's country/industry filters.
"""

from collections.abc import Iterable

from job_agent.discovery.base import DiscoveryQuery
from job_agent.models.company import CompanyTarget


class SeedDiscoverer:
    def __init__(self, companies: Iterable[CompanyTarget]) -> None:
        self._companies = list(companies)

    def discover(self, query: DiscoveryQuery) -> list[CompanyTarget]:
        return [c for c in self._companies if query.matches(c)]
