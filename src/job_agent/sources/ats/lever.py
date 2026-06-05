"""Lever adapter — common for startups/scale-ups across Europe.

Public postings API (verified live): ``https://api.lever.co/v0/postings/{handle}?mode=json``
returns a top-level JSON array of postings. No auth.
"""

from __future__ import annotations

import json
from typing import Any

from job_agent.models.company import CompanyTarget
from job_agent.models.job import Job
from job_agent.sources.base import classify_employment


class LeverAdapter:
    def feed_url(self, handle: str) -> str:
        return f"https://api.lever.co/v0/postings/{handle}?mode=json"

    def parse(self, body: str, company: CompanyTarget) -> list[Job]:
        postings: list[dict[str, Any]] = json.loads(body)
        jobs: list[Job] = []
        for p in postings:
            ext_id = str(p.get("id", "")).strip()
            title = (p.get("text") or "").strip()
            if not ext_id or not title:
                continue
            categories = p.get("categories") or {}
            jobs.append(
                Job(
                    source="lever",
                    external_id=ext_id,
                    title=title,
                    company=company.name,
                    country=company.country,
                    city=categories.get("location"),
                    source_type="niche",
                    description=p.get("descriptionPlain", "") or "",
                    url=p.get("hostedUrl") or p.get("applyUrl"),
                    employment_type=classify_employment(title, categories.get("commitment")),
                )
            )
        return jobs
