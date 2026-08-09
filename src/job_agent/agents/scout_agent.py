"""Scout Agent — the multi-source orchestrator.

Adapts the reference project's ScoutAgent (dispatch table + "one source's failure
must not abort the others" resilience + RunContext/observability wrapper) to this
product's layered sources:

- Track A (company-first): run each ``CompanyDiscoverer``, then pull every
  discovered company's ATS feed.
- Track B (board): pull international-organisation roles per hub country.

Every collaborator is a dependency-injection seam; with the in-memory store/obs
and a fixture ``http_get`` the whole agent runs offline with zero live calls.
"""

from __future__ import annotations

from collections import Counter
from collections.abc import Callable
from dataclasses import dataclass

from pydantic import BaseModel, Field

from job_agent.discovery.base import CompanyDiscoverer, DiscoveryQuery
from job_agent.models.company import ATSPlatform, CompanyTarget
from job_agent.models.job import Job
from job_agent.observability import ObservabilityStore, start_run
from job_agent.persistence import JobStore, dedupe_jobs
from job_agent.sources import HttpGet, fetch_company_jobs
from job_agent.sources.ats.workday import JsonPost, fetch_workday_jobs
from job_agent.sources.board import BoardSource
from job_agent.sources.crawl.career_page import CareerPageCrawler
from job_agent.visa.signal import VisaSignalClassifier


@dataclass
class ScoutQuery:
    """One scouting request — the same query drives every layer.

    ``discovery`` carries country / industry / keywords / broad. Track A companies
    come from the agent's discoverers; Track A aggregators and Track B
    international organisations come from the agent's board sources.
    """

    discovery: DiscoveryQuery


class ScoutResult(BaseModel):
    """Summary of a single Scout run."""

    jobs: list[Job]
    fetched: int
    stored: int
    errors: list[str]
    diagnostics: dict[str, object] = Field(default_factory=dict)


# Type alias for the injectable ATS fetch function (keeps the signature explicit).
AtsFetch = Callable[[CompanyTarget, HttpGet], list[Job]]


class ScoutAgent:
    def __init__(
        self,
        *,
        http_get: HttpGet,
        discoverers: list[CompanyDiscoverer] | None = None,
        board_sources: list[BoardSource] | None = None,
        store: JobStore | None = None,
        obs: ObservabilityStore | None = None,
        ats_fetch: AtsFetch = fetch_company_jobs,
        workday_post: JsonPost | None = None,
        career_crawler: CareerPageCrawler | None = None,
        classifier: VisaSignalClassifier | None = None,
    ) -> None:
        self._http_get = http_get
        self._discoverers = discoverers or []
        self._board_sources = board_sources or []
        self._store = store
        self._obs = obs
        self._ats_fetch = ats_fetch
        self._workday_post = workday_post
        self._career_crawler = career_crawler
        self._classifier = classifier

    def run(self, query: ScoutQuery) -> ScoutResult:
        """Fetch across Track A + Track B, dedupe, persist, return a summary."""
        ctx = start_run("scout")
        if self._obs:
            self._obs.insert_run(ctx)
        try:
            result = self._do_run(query)
            if self._obs:
                self._obs.finish_run(ctx.run_id, "success")
            return result
        except Exception as exc:  # pragma: no cover - guard mirrors reference
            if self._obs:
                self._obs.finish_run(ctx.run_id, "error", str(exc)[:500])
            raise

    def _do_run(self, query: ScoutQuery) -> ScoutResult:
        jobs: list[Job] = []
        errors: list[str] = []

        # --- Track A: discover companies, then fetch each one's ATS feed ---
        companies: list[CompanyTarget] = []
        for discoverer in self._discoverers:
            try:
                companies.extend(discoverer.discover(query.discovery))
            except Exception as exc:  # noqa: BLE001 - one discoverer must not abort the rest
                errors.append(f"discovery {type(discoverer).__name__}: {type(exc).__name__}: {exc}")

        fetch_attempts = 0
        fetch_successes = 0
        for company in companies:
            fetch_attempts += 1
            try:
                if company.ats is ATSPlatform.workday and self._workday_post is not None:
                    fetched_jobs = fetch_workday_jobs(company, self._workday_post)
                elif company.ats is ATSPlatform.unknown and self._career_crawler is not None:
                    fetched_jobs = self._career_crawler.crawl(company)
                else:
                    fetched_jobs = self._ats_fetch(company, self._http_get)
                jobs.extend(fetched_jobs)
                if fetched_jobs:
                    fetch_successes += 1
            except Exception as exc:  # noqa: BLE001 - one company must not abort the rest
                errors.append(f"{company.name} [{company.ats}]: {type(exc).__name__}: {exc}")

        # --- Board sources: Layer-1 aggregators + Track B international orgs ---
        for source in self._board_sources:
            try:
                jobs.extend(source.fetch(query.discovery))
            except Exception as exc:  # noqa: BLE001 - one source must not abort the rest
                errors.append(f"{source.name}: {type(exc).__name__}: {exc}")

        fetched = len(jobs)
        deduped = dedupe_jobs(jobs)
        # Job-level enrichment (candidate-independent): tag each with a visa signal.
        if self._classifier is not None:
            deduped = self._classifier.enrich_jobs(deduped)
        stored = self._store.upsert_jobs(deduped) if self._store is not None else len(deduped)
        discovery_stats = {
            type(discoverer).__name__: dict(getattr(discoverer, "stats", {}))
            for discoverer in self._discoverers
            if getattr(discoverer, "stats", None)
        }
        diagnostics: dict[str, object] = {
            "discovered_companies": len(companies),
            "company_fetch_attempts": fetch_attempts,
            "company_fetch_successes": fetch_successes,
            "jobs_by_source": dict(Counter(job.source for job in deduped)),
            "ats_by_platform": dict(Counter(company.ats.value for company in companies)),
            "employment_by_type": dict(Counter(job.employment_type.value for job in deduped)),
            "discovery": discovery_stats,
        }
        return ScoutResult(
            jobs=deduped, fetched=fetched, stored=stored, errors=errors,
            diagnostics=diagnostics,
        )
