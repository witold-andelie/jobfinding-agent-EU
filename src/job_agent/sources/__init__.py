"""Job sources, organised in layers (see README):

- Layer 1 ``aggregators`` — EURES, national public employment services (breadth).
- Layer 2 ``ats`` — applicant-tracking-system feeds, keyed per company (SME long tail).
- Layer 3 ``crawl`` — Playwright career-page crawling (last resort).

All sources are dependency-injection seams: network access is passed in as an
``HttpGet`` callable so every adapter is unit-testable offline with fixtures.
"""

from job_agent.sources.base import HttpGet
from job_agent.sources.ats import ADAPTERS, fetch_company_jobs

__all__ = ["ADAPTERS", "HttpGet", "fetch_company_jobs"]
