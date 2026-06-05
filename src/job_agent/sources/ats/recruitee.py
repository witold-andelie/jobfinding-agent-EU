"""Recruitee adapter — common among NL/DACH SMEs.

Public offers API (verified live): ``https://{handle}.recruitee.com/api/offers/``
returns ``{"offers": [...]}``. No auth.
"""

from __future__ import annotations

import json
from typing import Any

from job_agent.models.company import CompanyTarget
from job_agent.models.job import Job
from job_agent.sources.base import classify_employment


class RecruiteeAdapter:
    def feed_url(self, handle: str) -> str:
        return f"https://{handle}.recruitee.com/api/offers/"

    def parse(self, body: str, company: CompanyTarget) -> list[Job]:
        data: dict[str, Any] = json.loads(body)
        jobs: list[Job] = []
        for offer in data.get("offers", []):
            ext_id = str(offer.get("id", "")).strip()
            title = (offer.get("title") or "").strip()
            if not ext_id or not title:
                continue
            jobs.append(
                Job(
                    source="recruitee",
                    external_id=ext_id,
                    title=title,
                    company=company.name,
                    country=company.country,
                    city=offer.get("city") or offer.get("location"),
                    source_type="niche",
                    description=offer.get("description", "") or "",
                    url=offer.get("careers_url") or offer.get("careers_apply_url"),
                    employment_type=classify_employment(title, offer.get("employment_type_code")),
                )
            )
        return jobs
