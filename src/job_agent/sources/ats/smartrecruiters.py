"""SmartRecruiters public postings API adapter."""

import json
from typing import Any

from job_agent.models.company import CompanyTarget
from job_agent.models.job import Job
from job_agent.sources.base import classify_employment


class SmartRecruitersAdapter:
    def feed_url(self, handle: str) -> str:
        return f"https://api.smartrecruiters.com/v1/companies/{handle}/postings?limit=100"

    def parse(self, body: str, company: CompanyTarget) -> list[Job]:
        data: dict[str, Any] = json.loads(body)
        jobs: list[Job] = []
        for posting in data.get("content", []):
            ext_id = str(posting.get("id") or "").strip()
            title = (posting.get("name") or "").strip()
            if not ext_id or not title:
                continue
            location = posting.get("location") or {}
            jobs.append(Job(
                source="smartrecruiters", external_id=ext_id, title=title,
                company=company.name, country=company.country,
                city=location.get("city") or location.get("country"), source_type="niche",
                url=posting.get("ref") or f"https://jobs.smartrecruiters.com/{company.name}/{ext_id}",
                employment_type=classify_employment(title),
            ))
        return jobs
