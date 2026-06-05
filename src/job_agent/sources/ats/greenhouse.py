"""Greenhouse adapter — common for tech companies and scale-ups across Europe.

Public JSON board API: ``https://boards-api.greenhouse.io/v1/boards/{handle}/jobs``
(append ``?content=true`` for descriptions). No auth required.
"""

import json
from typing import Any

from job_agent.models.company import CompanyTarget
from job_agent.models.job import Job
from job_agent.sources.base import classify_employment


class GreenhouseAdapter:
    def feed_url(self, handle: str) -> str:
        return f"https://boards-api.greenhouse.io/v1/boards/{handle}/jobs?content=true"

    def parse(self, body: str, company: CompanyTarget) -> list[Job]:
        data: dict[str, Any] = json.loads(body)
        jobs: list[Job] = []
        for j in data.get("jobs", []):
            ext_id = str(j.get("id", "")).strip()
            if not ext_id:
                continue
            title = (j.get("title") or "").strip()
            location = (j.get("location") or {}).get("name")
            jobs.append(
                Job(
                    source="greenhouse",
                    external_id=ext_id,
                    title=title,
                    company=company.name,
                    country=company.country,
                    city=location or None,
                    source_type="niche",
                    description=j.get("content", "") or "",
                    url=j.get("absolute_url"),
                    employment_type=classify_employment(title),
                )
            )
        return jobs
