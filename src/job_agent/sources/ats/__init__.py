"""Layer 2 — ATS feed adapters.

Each adapter knows one applicant-tracking system: how to build the public feed URL
for a company handle, and how to parse that feed into normalised ``Job`` objects.
This is how we reach the SME long tail (companies that post only on their own ATS,
not on LinkedIn/aggregators).
"""

from job_agent.models.company import ATSPlatform, CompanyTarget
from job_agent.models.job import Job
from job_agent.sources.ats.base import ATSAdapter
from job_agent.sources.ats.greenhouse import GreenhouseAdapter
from job_agent.sources.ats.lever import LeverAdapter
from job_agent.sources.ats.personio import PersonioAdapter
from job_agent.sources.ats.recruitee import RecruiteeAdapter
from job_agent.sources.base import HttpGet

# Registry: extend this as we add adapters (softgarden needs per-tenant tokens; workday...).
ADAPTERS: dict[ATSPlatform, ATSAdapter] = {
    ATSPlatform.personio: PersonioAdapter(),
    ATSPlatform.greenhouse: GreenhouseAdapter(),
    ATSPlatform.lever: LeverAdapter(),
    ATSPlatform.recruitee: RecruiteeAdapter(),
}


def fetch_company_jobs(company: CompanyTarget, http_get: HttpGet) -> list[Job]:
    """Fetch and normalise all open jobs for one company via its ATS.

    Returns ``[]`` (never raises) when the company has no detected ATS or no
    handle — the caller (Scout) can then route it to the Layer 3 page crawler.
    """
    adapter = ADAPTERS.get(company.ats)
    if adapter is None or company.ats_handle is None:
        return []
    body = http_get(adapter.feed_url(company.ats_handle))
    return adapter.parse(body, company)


__all__ = ["ADAPTERS", "ATSAdapter", "fetch_company_jobs"]
