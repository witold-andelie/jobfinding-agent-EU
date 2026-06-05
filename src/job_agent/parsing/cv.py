"""Extract a structured profile from raw CV text (DeepSeek chat).

Nationality is deliberately NOT inferred from a CV — it is rarely stated reliably,
yet it is the key visa input — so the parser extracts only CV-derivable fields and
``to_profile`` merges in the nationality the user supplies separately. The LLM is
told not to invent skills/experience; network lives in the injected ``ask`` seam,
so this is unit-testable offline.
"""

from __future__ import annotations

import json
import re
from dataclasses import dataclass
from dataclasses import field as dc_field

from job_agent.models.candidate import CandidateProfile, Track

_PROMPT = (
    "Extract a structured profile from this CV. Use ISO codes: alpha-2 for country, "
    "ISO-639-1 for languages (e.g. en, fr, de). Infer degree_country from where the "
    "highest degree was obtained (null if unclear). Estimate years_experience as a "
    "number. Do NOT invent skills or experience that are not in the CV. Copy the "
    "experience and education lines VERBATIM from the CV — do not paraphrase.\n"
    'Reply with ONLY JSON: {{"name": "", "contact": "", "field": "", "skills": [], '
    '"languages": [], "years_experience": 0, "degree_country": null, '
    '"experience": [], "education": [], "summary": ""}}.\n\nCV:\n{cv}'
)


@dataclass
class ParsedCV:
    field: str = ""
    skills: list[str] = dc_field(default_factory=list)
    languages: list[str] = dc_field(default_factory=list)
    years_experience: float = 0.0
    degree_country: str | None = None
    summary: str = ""
    name: str = ""
    contact: str = ""
    experience: list[str] = dc_field(default_factory=list)  # verbatim lines
    education: list[str] = dc_field(default_factory=list)    # verbatim lines


def _to_float(value: object) -> float:
    try:
        return float(value)  # type: ignore[arg-type]
    except (TypeError, ValueError):
        return 0.0


def _norm_country(value: object) -> str | None:
    if isinstance(value, str) and len(value.strip()) == 2:
        return value.strip().upper()
    return None


def parse_cv(cv_text: str, ask) -> ParsedCV:  # ask: Callable[[str], str]
    """Parse ``cv_text`` into a ``ParsedCV``; degrades to empty on bad LLM output."""
    raw = ask(_PROMPT.format(cv=cv_text[:8000]))
    match = re.search(r"\{.*\}", raw, re.DOTALL)
    if not match:
        return ParsedCV(summary="(could not parse CV)")
    try:
        data = json.loads(match.group(0))
    except json.JSONDecodeError:
        return ParsedCV(summary="(unparseable CV analysis)")
    return ParsedCV(
        field=str(data.get("field", "")),
        skills=[str(s) for s in data.get("skills", [])],
        languages=[str(lang).lower() for lang in data.get("languages", [])],
        years_experience=_to_float(data.get("years_experience", 0)),
        degree_country=_norm_country(data.get("degree_country")),
        summary=str(data.get("summary", "")),
        name=str(data.get("name", "")),
        contact=str(data.get("contact", "")),
        experience=[str(e) for e in data.get("experience", [])],
        education=[str(e) for e in data.get("education", [])],
    )


def to_profile(
    parsed: ParsedCV,
    nationality: str,
    *,
    tracks: list[Track] | None = None,
    degree_country: str | None = None,
) -> CandidateProfile:
    """Merge a ParsedCV with the user-supplied nationality into a CandidateProfile.

    ``degree_country`` overrides the parsed value when the user knows better.
    """
    return CandidateProfile(
        nationality=nationality,
        degree_country=degree_country if degree_country is not None else parsed.degree_country,
        field=parsed.field,
        skills=parsed.skills,
        languages=parsed.languages,
        years_experience=parsed.years_experience,
        tracks=tracks or [Track.private],
    )
