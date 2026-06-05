"""EURES board source — the EU job-mobility portal.

One source spanning EU/EEA, which is the highest-leverage breadth play: a single
adapter reaches DE/NL/FR/AT/BE/LU/CZ/PL/DK/IT at once (Switzerland is not in EURES
— see JobRoomSource).

NOTE: EURES vacancy access in production requires partner credentials; the injected
transport supplies them as a header. The response shape below is defensive and must
be verified against the live API — the offline fixture exercises this mapping.
"""

from __future__ import annotations

import json
from typing import Any

from job_agent.discovery.base import DiscoveryQuery
from job_agent.models.job import Job
from job_agent.sources.base import classify_employment
from job_agent.sources.board import HttpJson

_BASE_URL = "https://europa.eu/eures/eures-apps/searchengine/page/jv-search/search"


def _normalize(raw: dict[str, Any]) -> Job | None:
    external_id = raw.get("id") or raw.get("reference")
    title = raw.get("title")
    if not external_id or not title:
        return None
    loc = raw.get("locationMap") if isinstance(raw.get("locationMap"), dict) else {}
    employer = raw.get("employer") if isinstance(raw.get("employer"), dict) else {}
    return Job(
        source="eures",
        external_id=str(external_id),
        title=title,
        company=employer.get("name") or raw.get("employerName") or "",
        country=(loc.get("countryCode") or raw.get("countryCode") or "").upper(),
        city=loc.get("city"),
        source_type="eures",
        description=raw.get("description", "") or "",
        url=raw.get("url"),
        employment_type=classify_employment(title),
    )


class EuresSource:
    name = "eures"

    def __init__(self, http: HttpJson, page_size: int = 50) -> None:
        self._http = http
        self._page_size = page_size

    def fetch(self, query: DiscoveryQuery) -> list[Job]:
        params = {
            "keywords": " ".join(query.keywords),
            "countryCode": (query.country or "").upper(),
            "resultsPerPage": str(self._page_size),
            "page": "1",
        }
        import urllib.parse

        url = f"{_BASE_URL}?{urllib.parse.urlencode(params)}"
        data = json.loads(self._http(url, None))
        items = data.get("jvs") or data.get("items") or []
        jobs = (_normalize(r) for r in items)
        return [j for j in jobs if j is not None]
