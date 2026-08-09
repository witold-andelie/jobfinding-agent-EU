"""ATS fingerprinting — the 'broad search' route.

Given a company's careers-page HTML or URL, detect which ATS it runs and extract
the tenant handle. This is what lets us reach companies we don't have on any seed
list: crawl a domain, fingerprint it, and we can now pull its structured feed.
"""

import re

from job_agent.discovery.base import DiscoveryQuery
from job_agent.models.company import ATSPlatform, CompanyTarget
from job_agent.sources.base import HttpGet

# platform -> regex whose first group captures the tenant handle (if any).
_PATTERNS: list[tuple[ATSPlatform, re.Pattern[str]]] = [
    (ATSPlatform.personio, re.compile(r"https?://([\w-]+)\.jobs\.personio\.(?:de|com)")),
    (ATSPlatform.greenhouse, re.compile(r"boards(?:-api)?\.greenhouse\.io/(?:v1/boards/)?([\w-]+)")),
    (ATSPlatform.greenhouse, re.compile(r"greenhouse\.io/embed/job_board\?for=([\w-]+)")),
    (ATSPlatform.lever, re.compile(r"jobs\.lever\.co/([\w-]+)")),
    (ATSPlatform.recruitee, re.compile(r"([\w-]+)\.recruitee\.com")),
    (ATSPlatform.ashby, re.compile(r"jobs\.ashbyhq\.com/([\w-]+)")),
    (ATSPlatform.workable, re.compile(r"apply\.workable\.com/([\w-]+)")),
    (ATSPlatform.smartrecruiters, re.compile(r"careers\.smartrecruiters\.com/([\w-]+)")),
    (ATSPlatform.workday, re.compile(r"([\w-]+)\.[\w-]+\.myworkdayjobs\.com")),
]
_WORKDAY_URL = re.compile(
    r"https?://([\w-]+)\.([\w-]+)\.myworkdayjobs\.com/[^/]+/([^/?#]+)",
    re.IGNORECASE,
)


def detect_ats(text: str) -> tuple[ATSPlatform, str | None]:
    """Return ``(platform, handle)`` for the first ATS fingerprint found in ``text``.

    ``text`` can be a careers URL or full page HTML. Returns
    ``(ATSPlatform.unknown, None)`` when nothing matches.
    """
    workday = _WORKDAY_URL.search(text)
    if workday:
        tenant, dc, site = workday.groups()
        return ATSPlatform.workday, f"{tenant}|{dc}|{site}"
    for platform, pattern in _PATTERNS:
        m = pattern.search(text)
        if m:
            return platform, m.group(1)
    return ATSPlatform.unknown, None


class AtsDetectDiscoverer:
    """Discovers ATS handles by fetching each seed company's careers page.

    Takes companies that have a ``careers_url`` (or ``website``) but no ATS yet,
    fetches the page via the injected ``HttpGet``, fingerprints it, and returns
    enriched ``CompanyTarget`` copies. Companies where nothing is detected are
    returned unchanged (Scout routes them to the Layer-3 crawler).
    """

    def __init__(self, companies: list[CompanyTarget], http_get: HttpGet) -> None:
        self._companies = companies
        self._http_get = http_get

    def discover(self, query: DiscoveryQuery) -> list[CompanyTarget]:
        out: list[CompanyTarget] = []
        for company in self._companies:
            if not query.matches(company):
                continue
            target = company.careers_url or company.website
            if company.ats is ATSPlatform.unknown and target:
                page = self._http_get(target)
                platform, handle = detect_ats(page or target)
                if platform is not ATSPlatform.unknown:
                    company = company.model_copy(
                        update={"ats": platform, "ats_handle": handle,
                                "discovered_via": "ats_crawl"}
                    )
            out.append(company)
        return out
