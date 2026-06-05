"""Workday adapter — large corporates (e.g. Doosan Bobcat at jobs.doosan.com).

Workday differs from the other ATS in two ways, so it lives outside the GET-based
``ADAPTERS`` registry and the handle-probe model:
1. Its job feed is a **POST** to the CXS endpoint (verified live on nvidia):
   ``POST https://{tenant}.{dc}.myworkdayjobs.com/wday/cxs/{tenant}/{site}/jobs``
   with body ``{"appliedFacets":{},"limit":N,"offset":0,"searchText":""}``.
2. The "handle" is three parts — ``tenant|dc|site`` (e.g.
   ``nvidia|wd5|NVIDIAExternalCareerSite``) — which can't be guessed from a company
   name, so Workday companies must be configured explicitly (not auto-probed).
"""

from __future__ import annotations

import json
from collections.abc import Mapping
from typing import Any, Callable

from job_agent.models.company import ATSPlatform, CompanyTarget
from job_agent.models.job import Job
from job_agent.sources.base import classify_employment

# (url, json_body, headers) -> response text.
JsonPost = Callable[[str, dict, Mapping[str, str] | None], str]


def parse_handle(handle: str) -> tuple[str, str, str] | None:
    """Split a ``tenant|dc|site`` handle; return None if malformed."""
    parts = (handle or "").split("|")
    return (parts[0], parts[1], parts[2]) if len(parts) == 3 and all(parts) else None


class WorkdayAdapter:
    def feed_url(self, tenant: str, dc: str, site: str) -> str:
        return f"https://{tenant}.{dc}.myworkdayjobs.com/wday/cxs/{tenant}/{site}/jobs"

    def parse(self, body: str, company: CompanyTarget, tenant: str, dc: str, site: str) -> list[Job]:
        data: dict[str, Any] = json.loads(body)
        base = f"https://{tenant}.{dc}.myworkdayjobs.com/en-US/{site}"
        jobs: list[Job] = []
        for posting in data.get("jobPostings", []):
            title = (posting.get("title") or "").strip()
            path = posting.get("externalPath") or ""
            if not title or not path:
                continue
            ext_id = path.rsplit("_", 1)[-1] if "_" in path else path
            jobs.append(
                Job(
                    source="workday",
                    external_id=ext_id,
                    title=title,
                    company=company.name,
                    country=company.country,
                    city=posting.get("locationsText"),
                    source_type="corporate",
                    url=f"{base}{path}",
                    employment_type=classify_employment(title),
                )
            )
        return jobs


def fetch_workday_jobs(company: CompanyTarget, post: JsonPost, *, limit: int = 20) -> list[Job]:
    """Fetch a Workday company's jobs via the CXS POST API.

    Returns ``[]`` (never raises here) when the company isn't a properly-configured
    Workday target.
    """
    parsed = parse_handle(company.ats_handle or "")
    if company.ats is not ATSPlatform.workday or parsed is None:
        return []
    tenant, dc, site = parsed
    adapter = WorkdayAdapter()
    body = post(
        adapter.feed_url(tenant, dc, site),
        {"appliedFacets": {}, "limit": limit, "offset": 0, "searchText": ""},
        None,
    )
    return adapter.parse(body, company, tenant, dc, site)
