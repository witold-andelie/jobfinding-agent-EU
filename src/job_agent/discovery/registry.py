"""Business-register discovery — the 'brute force' company-list source.

Step 1 covers **Czechia (ARES)** and **Switzerland (Zefix)**, built to the live API
shapes (probed 2026). Hard realities, encoded honestly:
- ARES is free + unauthenticated; Zefix **requires a registered API account**
  (Basic auth via ``Settings.zefix_auth_header``).
- Registries return company name/seat but **not a website**, so a downstream
  ``DomainResolver`` is needed before the career-page crawl can run.
- Industry filtering is weak: ARES NACE codes are finicky (name keyword is the
  pragmatic filter); Zefix has no industry filter at all (name only).

Each client takes an injected ``JsonPost`` transport, so all of this is unit-testable
offline with fixtures and makes zero live calls in tests.
"""

from __future__ import annotations

import json
from collections.abc import Mapping
from dataclasses import dataclass, field
from typing import Callable, Protocol

from job_agent.discovery.base import DiscoveryQuery
from job_agent.models.company import CompanyTarget

# (url, json_body, headers) -> response text.
JsonPost = Callable[[str, dict, Mapping[str, str] | None], str]

_ARES_URL = "https://ares.gov.cz/ekonomicke-subjekty-v-be/rest/ekonomicke-subjekty/vyhledat"
_ZEFIX_URL = "https://www.zefix.admin.ch/ZefixPublicREST/api/v1/firm/search.json"


@dataclass
class CompanyRecord:
    """A company as returned by a business register (no website — see module docs)."""

    name: str
    country: str  # ISO-2
    registry_id: str | None = None  # ARES IČO / Zefix UID
    city: str | None = None
    nace: list[str] = field(default_factory=list)
    website: str | None = None
    source: str = ""  # "ares" | "zefix"


class RegistryClient(Protocol):
    name: str
    country: str

    def search(
        self, keyword: str | None = None, nace: list[str] | None = None, limit: int = 20
    ) -> list[CompanyRecord]: ...


class AresClient:
    """Czech business register (ARES). Free, unauthenticated."""

    name = "ares"
    country = "CZ"

    def __init__(self, post: JsonPost) -> None:
        self._post = post

    def search(
        self, keyword: str | None = None, nace: list[str] | None = None, limit: int = 20
    ) -> list[CompanyRecord]:
        body: dict = {"pocet": limit, "start": 0}
        if keyword:
            body["obchodniJmeno"] = keyword
        if nace:
            body["czNace"] = list(nace)
        data = json.loads(self._post(_ARES_URL, body, None))
        records: list[CompanyRecord] = []
        for subject in data.get("ekonomickeSubjekty", []):
            name = subject.get("obchodniJmeno")
            if not name:
                continue
            sidlo = subject.get("sidlo") or {}
            records.append(
                CompanyRecord(
                    name=name,
                    country="CZ",
                    registry_id=subject.get("ico"),
                    city=sidlo.get("nazevObce"),
                    nace=[str(c) for c in (subject.get("czNace") or [])],
                    source="ares",
                )
            )
        return records


class ZefixClient:
    """Swiss central business name index (Zefix). Requires Basic-auth credentials.

    No industry filter — ``nace`` is ignored; search is by company name only.
    """

    name = "zefix"
    country = "CH"

    def __init__(self, post: JsonPost, auth_header: str | None = None) -> None:
        self._post = post
        self._auth = auth_header

    def search(
        self, keyword: str | None = None, nace: list[str] | None = None, limit: int = 20
    ) -> list[CompanyRecord]:
        headers = {"Authorization": self._auth} if self._auth else None
        body = {"name": keyword or "", "maxEntries": limit, "languageKey": "en"}
        data = json.loads(self._post(_ZEFIX_URL, body, headers))
        items = data.get("list", []) if isinstance(data, dict) else (data or [])
        records: list[CompanyRecord] = []
        for firm in items:
            name = firm.get("name")
            if not name:
                continue
            address = firm.get("address") if isinstance(firm.get("address"), dict) else {}
            records.append(
                CompanyRecord(
                    name=name,
                    country="CH",
                    registry_id=firm.get("uid") or firm.get("chid"),
                    city=firm.get("legalSeat") or address.get("city"),
                    source="zefix",
                )
            )
        return records


class RegistryDiscoverer:
    """Turn registry hits into ``CompanyTarget``s, routed by the query's country.

    Websites are unknown at this stage (``website=None``); the brute-force pipeline
    resolves them before crawling.
    """

    def __init__(self, clients: list[RegistryClient], limit: int = 20) -> None:
        self._clients = clients
        self._limit = limit

    def discover(self, query: DiscoveryQuery) -> list[CompanyTarget]:
        keyword = query.industry or (" ".join(query.keywords) or None)
        targets: list[CompanyTarget] = []
        for client in self._clients:
            if query.country and client.country.upper() != query.country.upper():
                continue
            for rec in client.search(keyword=keyword, limit=self._limit):
                targets.append(
                    CompanyTarget(
                        name=rec.name,
                        country=rec.country,
                        industry=query.industry,
                        website=rec.website,
                        discovered_via="registry",
                    )
                )
        return targets
