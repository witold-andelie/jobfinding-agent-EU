"""Brute-force search: registry → resolve domain → crawl careers page → jobs.

Ties the pieces together for "given a country + industry, find companies in the
business register and crawl their sites for openings". Honest about the gap: the
registry yields no website, so a ``DomainResolver`` must supply one (search-based or
heuristic). With the default ``NullResolver`` every company lands in ``unresolved`` —
plug a real resolver to make the crawl run.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Protocol

from job_agent.discovery.base import DiscoveryQuery
from job_agent.discovery.registry import RegistryDiscoverer
from job_agent.models.company import CompanyTarget
from job_agent.models.job import Job
from job_agent.persistence import dedupe_jobs
from job_agent.sources.crawl import CareerPageCrawler


class DomainResolver(Protocol):
    """Find a company's website. The missing link registries don't provide."""

    def resolve(self, company: CompanyTarget) -> str | None: ...


class NullResolver:
    """Default: resolves nothing — so the crawl is explicitly gated, never guessed."""

    def resolve(self, company: CompanyTarget) -> str | None:
        return None


@dataclass
class BruteForceResult:
    companies: list[CompanyTarget]
    jobs: list[Job]
    unresolved: list[str] = field(default_factory=list)  # company names with no website
    errors: list[str] = field(default_factory=list)


def brute_force_search(
    query: DiscoveryQuery,
    registry: RegistryDiscoverer,
    crawler: CareerPageCrawler | None = None,
    resolver: DomainResolver | None = None,
    *,
    max_companies: int = 50,
) -> BruteForceResult:
    """Run the full registry→resolve→crawl pipeline, with per-company isolation.

    ``crawler`` defaults to ``build_career_crawler()`` — a Scrapling-backed stealth/JS
    crawler when the ``scrape`` extra is installed, else the static fallback.
    """
    if crawler is None:
        from job_agent.sources.crawl import build_career_crawler

        crawler = build_career_crawler()
    resolver = resolver or NullResolver()
    companies = registry.discover(query)[:max_companies]
    jobs: list[Job] = []
    unresolved: list[str] = []
    errors: list[str] = []

    for company in companies:
        website = company.website or resolver.resolve(company)
        if not website:
            unresolved.append(company.name)
            continue
        resolved = company.model_copy(update={"website": website})
        try:
            jobs.extend(crawler.crawl(resolved))
        except Exception as exc:  # noqa: BLE001 - one company must not abort the sweep
            errors.append(f"{company.name}: {type(exc).__name__}: {exc}")

    return BruteForceResult(companies, dedupe_jobs(jobs), unresolved, errors)
