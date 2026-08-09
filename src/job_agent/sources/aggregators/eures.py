"""EURES board source — the EU job-mobility portal.

One source spanning EU/EEA, which is the highest-leverage breadth play: a single
adapter reaches DE/NL/FR/AT/BE/LU/CZ/PL/DK/IT at once (Switzerland is not in EURES
— see JobRoomSource).

The current public search endpoint is a POST API under ``https://europa.eu/eures/api``
and does not require partner credentials. The older portal GET path remains as a
fallback for injected legacy transports. The public endpoint is reverse-engineered
and may change without notice.
"""

from __future__ import annotations

import json
import uuid
from collections.abc import Callable, Mapping
from typing import Any

from job_agent.discovery.base import DiscoveryQuery
from job_agent.models.job import Job
from job_agent.sources.base import classify_employment
from job_agent.sources.board import HttpJson

_BASE_URL = "https://europa.eu/eures/eures-apps/searchengine/page/jv-search/search"
_PUBLIC_API_URL = "https://europa.eu/eures/api/jv-searchengine/public/jv-search/search"

# (url, json_body, headers) -> response text
JsonPost = Callable[[str, dict[str, Any], Mapping[str, str] | None], str]


def _normalize(raw: dict[str, Any]) -> Job | None:
    external_id = raw.get("id") or raw.get("reference")
    title = raw.get("title")
    if not external_id or not title:
        return None
    loc = raw.get("locationMap") if isinstance(raw.get("locationMap"), dict) else {}
    if "countryCode" in loc:
        country = str(loc.get("countryCode") or "").upper()
        city = loc.get("city")
    else:
        country = next(iter(loc), "").upper()
        city = raw.get("city")
    employer = raw.get("employer") if isinstance(raw.get("employer"), dict) else {}
    return Job(
        source="eures",
        external_id=str(external_id),
        title=title,
        company=employer.get("name") or raw.get("employerName") or "",
        country=country or str(raw.get("countryCode") or "").upper(),
        city=city,
        source_type="eures",
        description=raw.get("description", "") or "",
        url=raw.get("url") or (
            f"https://europa.eu/eures/api/jv-searchengine/public/jv/id/{external_id}"
            "?requestLang=en"
        ),
        employment_type=classify_employment(title),
    )


class EuresSource:
    name = "eures"

    def __init__(
        self,
        http: HttpJson,
        page_size: int = 50,
        post: JsonPost | None = None,
    ) -> None:
        self._http = http
        self._page_size = page_size
        self._post = post

    def fetch(self, query: DiscoveryQuery) -> list[Job]:
        if self._post is not None:
            keywords = [
                {"keyword": keyword, "specificSearchCode": "EVERYWHERE"}
                for keyword in query.keywords
            ]
            body: dict[str, Any] = {
                "resultsPerPage": min(self._page_size, 50),
                "page": 1,
                "sortSearch": "BEST_MATCH" if keywords else "MOST_RECENT",
                "keywords": keywords,
                "publicationPeriod": None,
                "occupationUris": [],
                "skillUris": [],
                "requiredExperienceCodes": [],
                "positionScheduleCodes": [],
                "sectorCodes": [],
                "educationAndQualificationLevelCodes": [],
                "positionOfferingCodes": [],
                "locationCodes": [query.country.lower()] if query.country else [],
                "euresFlagCodes": [],
                "otherBenefitsCodes": [],
                "requiredLanguages": [],
                "minNumberPost": None,
                "sessionId": f"eu-job-agent-{uuid.uuid4()}",
                "userPreferredLanguage": None,
                "requestLanguage": "en",
            }
            data = json.loads(self._post(_PUBLIC_API_URL, body, {"Accept": "application/json"}))
            items = data.get("jvs") if isinstance(data, dict) else []
            jobs = (_normalize(r) for r in items)
            return [j for j in jobs if j is not None]

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
