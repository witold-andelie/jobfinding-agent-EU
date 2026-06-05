"""Shared source primitives.

``HttpGet`` is the single network seam for the whole source layer: a callable that
takes a URL and returns the response body as text. Production passes a real HTTP
client; tests pass a function that returns fixture strings — so nothing here ever
touches the network in a unit test (mirrors the reference project's "0 live calls"
discipline).
"""

from collections.abc import Callable

from job_agent.models.job import EmploymentType

HttpGet = Callable[[str], str]


# Title keywords → employment type. Multilingual because we cover DE/FR/CZ/PL/...
_INTERN_HINTS = ("intern", "internship", "praktikum", "praktikant", "stage", "stáž", "staż")
_TRAINEE_HINTS = ("trainee", "traineeship", "graduate program", "absolvent", "werkstudent",
                  "working student", "apprentice", "ausbildung")


def classify_employment(title: str, raw_type: str | None = None) -> EmploymentType:
    """Best-effort employment-type classification from a job title / ATS field.

    Keyword-based and deliberately conservative; the LLM enrichment step can
    refine this later. Junior-relevant categories (internship/traineeship) are
    surfaced explicitly rather than buried in free text.
    """
    haystack = f"{title} {raw_type or ''}".lower()
    if any(h in haystack for h in _INTERN_HINTS):
        return EmploymentType.internship
    if any(h in haystack for h in _TRAINEE_HINTS):
        return EmploymentType.traineeship
    return EmploymentType.full_time
