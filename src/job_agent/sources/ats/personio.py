"""Personio adapter — the most common ATS among DACH Mittelstand SMEs.

Personio exposes a public XML feed per company at
``https://{handle}.jobs.personio.de/xml`` (also ``.jobs.personio.com`` for some
tenants). Each ``<position>`` carries id, office, department, employment type and
HTML descriptions. This single adapter unlocks a large slice of the German /
Austrian / Swiss SME long tail.
"""

import xml.etree.ElementTree as ET

from job_agent.models.company import CompanyTarget
from job_agent.models.job import Job
from job_agent.sources.base import classify_employment


def _text(node: ET.Element, tag: str) -> str:
    child = node.find(tag)
    return (child.text or "").strip() if child is not None and child.text else ""


def _descriptions(position: ET.Element) -> str:
    """Concatenate all <jobDescription><name>/<value> blocks into one string."""
    parts: list[str] = []
    for desc in position.findall(".//jobDescription"):
        name = _text(desc, "name")
        value = _text(desc, "value")
        if value:
            parts.append(f"{name}\n{value}" if name else value)
    return "\n\n".join(parts)


class PersonioAdapter:
    def feed_url(self, handle: str) -> str:
        return f"https://{handle}.jobs.personio.de/xml"

    def parse(self, body: str, company: CompanyTarget) -> list[Job]:
        root = ET.fromstring(body)
        jobs: list[Job] = []
        for pos in root.findall(".//position"):
            ext_id = _text(pos, "id")
            if not ext_id:
                continue
            title = _text(pos, "name")
            office = _text(pos, "office")
            handle = company.ats_handle
            jobs.append(
                Job(
                    source="personio",
                    external_id=ext_id,
                    title=title,
                    company=company.name,
                    country=company.country,
                    city=office or None,
                    source_type="niche",
                    description=_descriptions(pos),
                    url=f"https://{handle}.jobs.personio.de/job/{ext_id}" if handle else None,
                    employment_type=classify_employment(title, _text(pos, "employmentType")),
                )
            )
        return jobs
