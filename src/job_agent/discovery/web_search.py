"""Discover company career sites from ordinary web-search results.

ATS-domain search finds structured boards, but many smaller employers expose only a
career page on their own domain. This discoverer turns those search results into
company targets; ``CareerPageCrawler`` then handles static HTML, JS pages, and ATS
fingerprinting. Search remains injected so the whole path is offline-testable.
"""

from __future__ import annotations

import unicodedata
from collections.abc import Callable
from urllib.parse import urlparse

from job_agent.discovery.ats_search import COUNTRY_TERMS
from job_agent.discovery.base import DiscoveryQuery
from job_agent.discovery.query_planner import QueryPlanner
from job_agent.models.company import CompanyTarget

SearchFn = Callable[[str], list[str]]

_BLOCKED_HOSTS = frozenset({
    "linkedin.com", "www.linkedin.com", "indeed.com", "www.indeed.com",
    "glassdoor.com", "www.glassdoor.com", "stepstone.com", "jobs.cz",
    "jobrapido.com", "jooble.org", "arbeitnow.com", "eures.europa.eu",
    "expats.cz", "ziprecruiter.com", "ziprecruiter.de",
    "google.com", "www.google.com", "bing.com", "www.bing.com",
})
_ATS_HOST_MARKERS = ("greenhouse.io", "lever.co", "personio.", "recruitee.com",
                     "ashbyhq.com", "smartrecruiters.com", "myworkdayjobs.com")
_CAREER_PATH_MARKERS = ("career", "jobs", "job", "vacan", "karriere", "kariera",
                        "work-with-us", "join-us")

# Company-owned career portals that are not represented by a searchable public ATS
# feed. Keep this registry small and evidence-based; it is a coverage extension, not
# a replacement for generic web discovery.
CAREER_HOSTS: dict[str, dict[str, str]] = {
    "CZ": {"jobs.doosan.com": "Doosan Bobcat"},
}


def _host(url: str) -> str | None:
    parsed = urlparse(url)
    host = (parsed.hostname or "").lower().removeprefix("www.")
    return host or None


def _city_from_url(url: str, fallback: str, cities: list[str]) -> str:
    def plain(value: str) -> str:
        return "".join(
            char for char in unicodedata.normalize("NFKD", value.lower())
            if not unicodedata.combining(char)
        )

    url_plain = plain(url)
    for city in cities:
        if plain(city) in url_plain:
            return city
    return fallback


class CareerWebDiscoverer:
    def __init__(
        self,
        search_fn: SearchFn,
        *,
        cities: int = 3,
        max_companies: int = 30,
        query_planner: QueryPlanner | None = None,
    ) -> None:
        self._search = search_fn
        self._cities = cities
        self._max_companies = max_companies
        self._query_planner = query_planner
        self.stats: dict[str, int] = {}

    def discover(self, query: DiscoveryQuery) -> list[CompanyTarget]:
        self.stats = {"queries": 0, "result_urls": 0, "companies": 0}
        country = (query.country or "").upper()
        terms = (COUNTRY_TERMS.get(country) or [country.lower()])[:self._cities]
        found: dict[str, CompanyTarget] = {}
        if self._query_planner is not None:
            planned = self._query_planner(query, terms)
            search_specs = [(search, terms[0] if terms else country.lower()) for search in planned]
        else:
            search_specs = [
                (f'{city} (careers OR jobs OR hiring) {" ".join(query.keywords)}'.strip(), city)
                for city in terms
            ]
        for search, fallback_city in search_specs:
            self.stats["queries"] += 1
            query_companies = 0
            for url in self._search(search):
                self.stats["result_urls"] += 1
                host = _host(url)
                if not host or host in _BLOCKED_HOSTS:
                    continue
                if any(marker in host for marker in _ATS_HOST_MARKERS):
                    continue
                parsed = urlparse(url)
                if not (host.startswith(("careers.", "jobs."))
                        or any(marker in parsed.path.lower() for marker in _CAREER_PATH_MARKERS)):
                    continue
                if query_companies >= 5:
                    break
                found.setdefault(host, CompanyTarget(
                    name=host.split(".")[0].replace("-", " ").title(),
                    country=country,
                    website=f"https://{host}",
                    careers_url=url,
                    city_hint=_city_from_url(url, fallback_city, terms),
                    industry=query.industry,
                    discovered_via="web_search",
                ))
                query_companies += 1
        for host, company_name in CAREER_HOSTS.get(country, {}).items():
            for city in terms:
                self.stats["queries"] += 1
                query = f"site:{host} {city}"
                query_companies = 0
                for url in self._search(query):
                    self.stats["result_urls"] += 1
                    if _host(url) != host or query_companies >= 5:
                        continue
                    found.setdefault(host, CompanyTarget(
                        name=company_name,
                        country=country,
                        website=f"https://{host}",
                        careers_url=url,
                        city_hint=_city_from_url(url, fallback_city, terms),
                        discovered_via="web_search",
                    ))
                    query_companies += 1
        companies = list(found.values())[:self._max_companies]
        self.stats["companies"] = len(companies)
        return companies
