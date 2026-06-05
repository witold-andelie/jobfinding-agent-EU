"""Domain resolution — the missing link between a registry hit and a crawlable site.

Registries return a company name but no website, so we resolve it via web search.
``SearchDomainResolver`` uses the Brave Search API; it filters out aggregators,
registries, and social networks so it returns the company's own homepage, not a
LinkedIn/Glassdoor page. The HTTP call is an injected seam → offline-testable.
"""

from __future__ import annotations

import json
import re
from collections.abc import Mapping, MutableMapping
from pathlib import Path
from typing import Callable
from urllib.parse import urlencode, urlparse

from job_agent.models.company import CompanyTarget

_BRAVE_URL = "https://api.search.brave.com/res/v1/web/search"

# Hosts that are never a company's own site — aggregators, registries, directories,
# socials. Skip them when picking a result.
_BLOCKLIST = {
    "linkedin.com", "facebook.com", "instagram.com", "twitter.com", "x.com",
    "youtube.com", "xing.com", "wikipedia.org", "glassdoor.com", "indeed.com",
    "jobs.cz", "prace.cz", "startupjobs.cz", "ares.gov.cz", "justice.cz", "zefix.ch",
    "kompass.com", "dnb.com", "crunchbase.com", "bloomberg.com", "northdata.com",
    "kurzy.cz", "companywall.cz", "merk.cz", "europages.co.uk", "europages.com",
    # business directories that kept surfacing in live tests
    "opten.hu", "opten.cz", "cylex.cz", "cylex.com", "firmy.cz", "edb.cz", "hbi.cz",
    "najisto.cz", "zaba.cz", "mapy.cz", "google.com", "trustpilot.com", "yelp.com",
    "moneyhouse.ch", "local.ch", "search.ch",
}

# Generic words that don't identify a specific company (used for the name↔domain check).
_GENERIC = {
    "software", "solutions", "solution", "group", "holding", "company", "services",
    "service", "international", "systems", "system", "technologies", "technology",
    "consulting", "digital", "media", "labs", "studio", "ltd", "gmbh", "sro", "spol",
    "kft", "limited", "supplies", "development", "cee", "czech", "swiss", "europe",
    "global", "trading", "industries",
}

# (url, headers) -> response text.
Http = Callable[[str, Mapping[str, str] | None], str]


class FileCache(dict):
    """A dict that persists to a JSON file — so resolutions survive across runs and
    the (limited) Brave quota is never spent twice on the same company."""

    def __init__(self, path: str | Path) -> None:
        self._path = Path(path)
        super().__init__()
        if self._path.exists():
            self.update(json.loads(self._path.read_text(encoding="utf-8")))

    def __setitem__(self, key: str, value: object) -> None:
        super().__setitem__(key, value)
        self._path.write_text(json.dumps(self, ensure_ascii=False), encoding="utf-8")


def _acceptable(host: str) -> bool:
    host = host.lower().removeprefix("www.")
    return bool(host) and not any(host == b or host.endswith("." + b) for b in _BLOCKLIST)


def _name_tokens(name: str) -> list[str]:
    return [t for t in re.findall(r"[a-z0-9]{4,}", name.lower()) if t not in _GENERIC]


class SearchDomainResolver:
    """Resolve a company to its own homepage via Brave search.

    Quality guard (learnt from live testing): the chosen domain must share a
    distinctive token with the company name, otherwise we return ``None`` rather
    than crawl a same-named but unrelated company. Better unresolved than wrong.
    """

    def __init__(
        self,
        http: Http,
        token: str,
        *,
        count: int = 5,
        cache: MutableMapping[str, str | None] | None = None,
        max_calls: int | None = None,
    ) -> None:
        """``cache`` persists/avoids repeat lookups; ``max_calls`` caps live Brave
        requests for this session (the API has a small monthly quota). Both default
        to safe values: an in-memory cache and no per-session cap."""
        self._http = http
        self._token = token
        self._count = count
        self._cache: MutableMapping[str, str | None] = cache if cache is not None else {}
        self._max_calls = max_calls
        self.calls_made = 0  # live Brave requests actually issued

    def resolve(self, company: CompanyTarget) -> str | None:
        key = f"{company.name.lower()}|{company.country.upper()}"
        if key in self._cache:  # cached (including negative results) — no quota spent
            return self._cache[key]

        tokens = _name_tokens(company.name)
        if not tokens:  # nothing distinctive to verify against → don't spend a request
            self._cache[key] = None
            return None
        if self._max_calls is not None and self.calls_made >= self._max_calls:
            return None  # session budget exhausted — do NOT call Brave (quota guard)

        self.calls_made += 1
        result = self._search(company, tokens)
        self._cache[key] = result
        return result

    def _search(self, company: CompanyTarget, tokens: list[str]) -> str | None:
        query = f"{company.name} {company.country} official website"
        url = f"{_BRAVE_URL}?{urlencode({'q': query, 'count': self._count})}"
        headers = {"X-Subscription-Token": self._token, "Accept": "application/json"}
        try:
            data = json.loads(self._http(url, headers))
        except Exception:  # noqa: BLE001 - resolution failure is non-fatal (company skipped)
            return None
        for result in (data.get("web") or {}).get("results", []):
            host = urlparse(result.get("url", "")).netloc.lower().removeprefix("www.")
            if _acceptable(host) and any(tok in host.replace("-", "") for tok in tokens):
                return f"https://{host}"
        return None
