"""Find a company's careers page and extract job postings from raw HTML.

Heuristic and deliberately conservative. If the careers page turns out to run a
known ATS, we hand off to the structured ATS adapter (clean data) instead of
scraping HTML. Network + politeness are injected seams, so this is offline-testable.
"""

from __future__ import annotations

import hashlib
import re
from typing import Protocol
from urllib.parse import urljoin

from job_agent.discovery.fingerprint import detect_ats
from job_agent.models.company import ATSPlatform, CompanyTarget
from job_agent.models.job import Job
from job_agent.sources import HttpGet, fetch_company_jobs

# Multilingual hints that a link leads to a careers page (DE/FR/CZ/PL/EN).
_CAREERS_HINTS = ("career", "careers", "jobs", "vacanc", "karriere", "stellenangebote",
                  "stellen", "kariera", "kariéra", "volna-mista", "nabidka-prace",
                  "emploi", "offres", "praca", "join-us", "work-with-us")
# Hints that a specific link is an individual job posting.
_JOB_HINTS = ("/job", "/jobs/", "/stelle", "/position", "/vacanc", "/offre", "/pozice",
              "/praca", "/career", "job-", "stellenangebot")

_ANCHOR = re.compile(r'<a\b[^>]*\bhref=["\']([^"\']+)["\'][^>]*>(.*?)</a>', re.I | re.S)
_TAG = re.compile(r"<[^>]+>")


def _clean(text: str) -> str:
    return re.sub(r"\s+", " ", _TAG.sub("", text)).strip()


def find_careers_url(html: str, base_url: str) -> str | None:
    """Return the absolute URL of the careers page linked from ``html``, if any."""
    for href, text in _ANCHOR.findall(html):
        blob = f"{href} {text}".lower()
        if any(h in blob for h in _CAREERS_HINTS):
            return urljoin(base_url, href)
    return None


def _job_id(url: str, title: str) -> str:
    return hashlib.sha256((url or title).encode("utf-8")).hexdigest()[:16]


def extract_jobs(html: str, company: CompanyTarget, base_url: str) -> list[Job]:
    """Heuristically pull job postings out of a careers-page's HTML."""
    jobs: list[Job] = []
    seen: set[str] = set()
    for href, text in _ANCHOR.findall(html):
        title = _clean(text)
        if not title or len(title) < 3 or not any(h in href.lower() for h in _JOB_HINTS):
            continue
        url = urljoin(base_url, href)
        if url in seen:
            continue
        seen.add(url)
        jobs.append(
            Job(
                source="careerpage",
                external_id=_job_id(url, title),
                title=title,
                company=company.name,
                country=company.country,
                source_type="crawl",
                url=url,
            )
        )
    return jobs


class RobotsChecker(Protocol):
    def allowed(self, url: str) -> bool: ...


class RateLimiter(Protocol):
    def wait(self) -> None: ...


class AllowAllRobots:
    """Default: permits everything. Replace with a real robots.txt-respecting checker."""

    def allowed(self, url: str) -> bool:
        return True


class NoOpRateLimiter:
    """Default: no throttling (fine for tests). Production uses a real token bucket."""

    def wait(self) -> None:
        return None


class CareerPageCrawler:
    def __init__(
        self,
        http_get: HttpGet,
        robots: RobotsChecker | None = None,
        rate_limiter: RateLimiter | None = None,
    ) -> None:
        self._http = http_get
        self._robots = robots or AllowAllRobots()
        self._rate = rate_limiter or NoOpRateLimiter()

    def crawl(self, company: CompanyTarget) -> list[Job]:
        """Fetch the company's site, locate its careers page, and return any jobs.

        If the careers page runs a known ATS, hands off to the structured adapter;
        otherwise extracts jobs from the HTML. Returns ``[]`` (never raises) when
        there is no website or robots.txt disallows it.
        """
        site = company.website
        if not site or not self._robots.allowed(site):
            return []
        self._rate.wait()
        home = self._http(site)
        careers_url = find_careers_url(home, site) or site
        if not self._robots.allowed(careers_url):
            return []
        self._rate.wait()
        page = self._http(careers_url)

        platform, handle = detect_ats(page)
        if platform is not ATSPlatform.unknown and handle:
            ats_company = company.model_copy(update={"ats": platform, "ats_handle": handle})
            return fetch_company_jobs(ats_company, self._http)
        return extract_jobs(page, company, careers_url)
