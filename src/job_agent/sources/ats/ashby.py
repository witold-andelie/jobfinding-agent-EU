"""Ashby public job-board adapter."""

import json
from typing import Any

from job_agent.models.company import CompanyTarget
from job_agent.models.job import Job
from job_agent.sources.base import classify_employment


class AshbyAdapter:
    def feed_url(self, handle: str) -> str:
        return f"https://api.ashbyhq.com/posting-api/job-board/{handle}"

    def parse(self, body: str, company: CompanyTarget) -> list[Job]:
        data: dict[str, Any] = json.loads(body)
        jobs: list[Job] = []
        for posting in data.get("jobs", []):
            ext_id = str(posting.get("jobUrl") or posting.get("id") or "").strip()
            title = (posting.get("title") or "").strip()
            if not ext_id or not title:
                continue
            jobs.append(Job(
                source="ashby", external_id=ext_id, title=title, company=company.name,
                country=company.country, city=posting.get("location"), source_type="niche",
                description=posting.get("descriptionHtml") or posting.get("description", ""),
                url=posting.get("jobUrl") or posting.get("applyUrl"),
                employment_type=classify_employment(title),
            ))
        return jobs
