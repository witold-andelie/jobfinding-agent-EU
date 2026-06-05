"""Discovery query + the discoverer protocol."""

from dataclasses import dataclass, field
from typing import Protocol

from job_agent.models.candidate import Track
from job_agent.models.company import CompanyTarget


@dataclass
class DiscoveryQuery:
    """What the client is looking for.

    A narrow query sets ``country`` and/or ``industry``; a broad sweep sets
    ``broad=True`` and lets the discoverer fan out as wide as it can.
    """

    country: str | None = None  # ISO-2
    industry: str | None = None  # substring-matched against CompanyTarget.industry
    track: Track = Track.private
    keywords: list[str] = field(default_factory=list)
    broad: bool = False

    def matches(self, company: CompanyTarget) -> bool:
        """Whether a candidate company satisfies this query's filters."""
        if self.country and company.country.upper() != self.country.upper():
            return False
        if self.industry and self.industry.lower() not in (company.industry or "").lower():
            return False
        return True


class CompanyDiscoverer(Protocol):
    def discover(self, query: DiscoveryQuery) -> list[CompanyTarget]: ...
