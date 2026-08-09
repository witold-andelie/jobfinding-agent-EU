"""Discover hiring companies by SEARCHING the ATS domains — no names known upfront.

This is the discovery engine's core trick. Instead of starting from a registry full
of dead shells (ARES) or asking the user for company names, we search the public ATS
job-board domains across the target country's major cities
(``site:jobs.personio.de zürich``, ``site:jobs.lever.co geneva`` …). Every hit is a
company *actively hiring on an ATS right now*; the result URL carries the ATS handle,
so we can pull its structured feed immediately.

Yield scales with **breadth**: cities × ATS domains. The Brave web API caps a single
query at 20 results, so we widen instead — several cities and several ATS domains per
country. Each query is one Brave call (quota-aware: tune ``cities``).
"""

from __future__ import annotations

from collections.abc import Callable

from job_agent.discovery.base import DiscoveryQuery
from job_agent.discovery.fingerprint import detect_ats
from job_agent.models.company import ATSPlatform, CompanyTarget
from job_agent.models.job import Job

# search_fn(query) -> list of result URLs
SearchFn = Callable[[str], list[str]]

# Public ATS board domains to search (the handle lives in the result URL). Multiple
# domains per platform widen coverage (e.g. Personio's .de and .com tenants).
_ATS_DOMAINS: dict[ATSPlatform, list[str]] = {
    ATSPlatform.personio: ["jobs.personio.de", "jobs.personio.com"],
    ATSPlatform.greenhouse: ["boards.greenhouse.io", "job-boards.greenhouse.io"],
    ATSPlatform.lever: ["jobs.lever.co"],
    ATSPlatform.recruitee: ["recruitee.com"],
    ATSPlatform.ashby: ["jobs.ashbyhq.com"],
    ATSPlatform.smartrecruiters: ["careers.smartrecruiters.com"],
    ATSPlatform.workday: ["*.myworkdayjobs.com"],
}

# Per-country terms. The FIRST few are distinct major cities (used to widen the
# search); the rest are spelling variants used when filtering jobs by location.
COUNTRY_TERMS: dict[str, list[str]] = {
    "CZ": ["praha", "brno", "ostrava", "dobříš", "mladá boleslav", "plzeň",
           "olomouc", "liberec", "pardubice", "prague", "prag", "czech",
           "česko", "česká", "czechia"],
    "CH": ["zürich", "geneva", "basel", "bern", "lausanne",
           "zurich", "genève", "genf", "switzerland", "schweiz", "suisse", "svizzera"],
    "AT": ["wien", "graz", "linz", "salzburg", "vienna", "austria", "österreich"],
    "PL": ["warszawa", "kraków", "wrocław", "gdańsk", "warsaw", "krakow", "wroclaw",
           "poland", "polska"],
    "NL": ["amsterdam", "rotterdam", "utrecht", "eindhoven", "the hague", "den haag",
           "netherlands"],
    "DE": ["berlin", "münchen", "hamburg", "köln", "frankfurt", "munich",
           "germany", "deutschland"],
    "FR": ["paris", "lyon", "toulouse", "lille", "france", "français"],
    "BE": ["brussels", "bruxelles", "antwerp", "ghent", "belgium", "belgië"],
    "LU": ["luxembourg", "luxembourg city", "esch", "letzebuerg"],
    "DK": ["copenhagen", "aarhus", "odense", "denmark", "danmark"],
    "IT": ["milan", "rome", "turin", "bologna", "italy", "italia"],
    "ES": ["madrid", "barcelona", "valencia", "spain", "españa"],
    "PT": ["lisbon", "porto", "portugal"],
    "SE": ["stockholm", "gothenburg", "malmö", "sweden", "sverige"],
    "FI": ["helsinki", "tampere", "finland", "suomi"],
    "IE": ["dublin", "cork", "galway", "ireland"],
    "RO": ["bucharest", "cluj", "romania", "românia"],
    "HU": ["budapest", "hungary", "magyarország"],
    "GR": ["athens", "thessaloniki", "greece", "ellada"],
}

def _search_cities(country: str | None, n: int) -> list[str]:
    if not country:
        return [""]
    return (COUNTRY_TERMS.get(country.upper()) or [country])[:n]


class AtsSearchDiscoverer:
    def __init__(
        self,
        search_fn: SearchFn,
        *,
        platforms: list[ATSPlatform] | None = None,
        cities: int = 3,
        max_companies: int | None = None,
    ) -> None:
        self._search = search_fn
        self._platforms = platforms or list(_ATS_DOMAINS)
        self._cities = cities
        self._max_companies = max_companies
        self.stats: dict[str, int] = {}

    def discover(self, query: DiscoveryQuery) -> list[CompanyTarget]:
        self.stats = {"queries": 0, "result_urls": 0, "companies": 0}
        cities = _search_cities(query.country, self._cities)
        keywords = " ".join(query.keywords)
        found: dict[tuple[ATSPlatform, str], CompanyTarget] = {}
        per_query_limit = 8
        for platform in self._platforms:
            for domain in _ATS_DOMAINS.get(platform, []):
                for city in cities:
                    q = " ".join(p for p in (f"site:{domain}", city, keywords) if p)
                    self.stats["queries"] += 1
                    query_companies = 0
                    for url in self._search(q):
                        self.stats["result_urls"] += 1
                        plat, handle = detect_ats(url)
                        if plat is not ATSPlatform.unknown and handle:
                            if query_companies >= per_query_limit:
                                break
                            found.setdefault(
                                (plat, handle),
                                CompanyTarget(name=handle, country=query.country or "",
                                              industry=query.industry, ats=plat,
                                              ats_handle=handle, discovered_via="ats_search"),
                            )
                            query_companies += 1
        companies = list(found.values())
        if self._max_companies:
            companies = companies[:self._max_companies]
        self.stats["companies"] = len(companies)
        return companies


def keep_jobs_in_country(jobs: list[Job], country: str) -> list[Job]:
    """Filter jobs to a country without requiring a known city.

    Country is the primary boundary. City terms are only a fallback for legacy ATS
    rows whose country field is empty; a missing or unfamiliar city must not discard
    an otherwise country-matching vacancy.
    """
    target = country.upper()
    terms = COUNTRY_TERMS.get(target, [country.lower()])
    return [job for job in jobs
            if job.country.upper() == target
            or any(t in (job.city or "").lower() for t in terms)]
