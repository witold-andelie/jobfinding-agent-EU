"""ATS adapter protocol."""

from typing import Protocol

from job_agent.models.company import CompanyTarget
from job_agent.models.job import Job


class ATSAdapter(Protocol):
    """One applicant-tracking system.

    ``feed_url`` builds the public feed endpoint from a company's ATS handle;
    ``parse`` turns the raw response body into normalised jobs. Implementations
    must be pure (no I/O) — fetching is done by the caller via the injected
    ``HttpGet`` seam, keeping adapters trivially testable with fixtures.
    """

    def feed_url(self, handle: str) -> str: ...

    def parse(self, body: str, company: CompanyTarget) -> list[Job]: ...
