"""Arbeitsagentur (German Federal Employment Agency) board source.

Field mapping adapted from the reference project's ``normalize_arbeitsagentur``.
The public API key ``jobboerse-jobsuche`` is sent as a header by the injected
transport. List responses carry no description; enriching via the detail endpoint
is a later refinement (kept out to stay within one request per search here).
"""

from __future__ import annotations

import json
import urllib.parse
from collections.abc import Mapping
from typing import Any

from job_agent.discovery.base import DiscoveryQuery
from job_agent.models.job import Job
from job_agent.sources.base import classify_employment
from job_agent.sources.board import HttpJson

_BASE_URL = "https://rest.arbeitsagentur.de/jobboerse/jobsuche-service/pc/v4/jobs"
_API_KEY = "jobboerse-jobsuche"  # well-known public key, same as the reference


def _normalize(raw: dict[str, Any]) -> Job | None:
    external_id = raw.get("refnr") or raw.get("hashId")
    title = raw.get("titel") or raw.get("beruf")
    if not external_id or not title:
        return None
    arbeitsort = raw.get("arbeitsort") if isinstance(raw.get("arbeitsort"), dict) else {}
    return Job(
        source="arbeitsagentur",
        external_id=str(external_id),
        title=title,
        company=raw.get("arbeitgeber") or "",
        country="DE",
        city=arbeitsort.get("ort"),
        source_type="pes",
        url=f"https://www.arbeitsagentur.de/jobsuche/jobdetail/{external_id}",
        employment_type=classify_employment(title),
    )


class ArbeitsagenturSource:
    name = "arbeitsagentur"

    def __init__(self, http: HttpJson, page_size: int = 25) -> None:
        self._http = http
        self._page_size = page_size

    def _headers(self) -> Mapping[str, str]:
        return {"X-API-Key": _API_KEY, "Accept": "application/json"}

    def fetch(self, query: DiscoveryQuery) -> list[Job]:
        params: dict[str, str] = {"page": "1", "size": str(self._page_size)}
        if query.keywords:
            params["was"] = " ".join(query.keywords)
        url = f"{_BASE_URL}?{urllib.parse.urlencode(params)}"
        data = json.loads(self._http(url, self._headers()))
        jobs = (_normalize(r) for r in data.get("stellenangebote", []))
        return [j for j in jobs if j is not None]
