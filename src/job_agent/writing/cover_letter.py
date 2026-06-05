"""Cover-letter generation (DeepSeek chat).

Hard rule from the project plan: NO hallucinated experience. The prompt is grounded
strictly in the candidate's real profile and instructed not to invent anything;
``unsupported_claims`` is a light post-check that flags any 'experience with X' the
profile does not back up, so the caller can warn the user. Network lives in the
injected ``ask`` seam → unit-testable offline.
"""

from __future__ import annotations

import re

from job_agent.models.candidate import CandidateProfile
from job_agent.models.job import Job

_PROMPT = (
    "Write a concise, professional cover letter (about 250 words) for this candidate "
    "applying to this job. Ground it ONLY in the candidate's real background below — "
    "do NOT invent skills, employers, degrees, or experience. Write in {language}.\n"
    "Candidate: field={field}; skills={skills}; experience={years} years; "
    "languages={languages}.\n{emphasis}"
    "Job: {title} at {company} ({city}, {country}).\nJob description:\n{description}\n\n"
    "Return only the letter text, no preamble."
)


def generate_cover_letter(
    candidate: CandidateProfile,
    job: Job,
    ask,  # ask: Callable[[str], str]
    *,
    language: str = "English",
    emphasis: list[str] | None = None,
) -> str:
    """Generate a tailored cover letter grounded in the candidate's real profile."""
    emphasis_line = f"Emphasise: {'; '.join(emphasis)}.\n" if emphasis else ""
    prompt = _PROMPT.format(
        language=language,
        field=candidate.field or "(unspecified)",
        skills=", ".join(candidate.skills) or "(none listed)",
        years=candidate.years_experience,
        languages=", ".join(candidate.languages) or "(unspecified)",
        emphasis=emphasis_line,
        title=job.title,
        company=job.company,
        city=job.city or "",
        country=job.country,
        description=(job.description or "")[:4000],
    )
    return ask(prompt).strip()


def unsupported_claims(letter: str, candidate: CandidateProfile) -> list[str]:
    """Flag 'experience with/in X' phrases in the letter not backed by the profile.

    A deliberately conservative anti-fabrication check: it only inspects explicit
    'experience (with|in) ...' claims and matches them against the candidate's
    skills/field tokens. Returns the unsupported claim phrases (empty = clean).
    """
    backed = {t for s in candidate.skills for t in re.findall(r"[a-zA-Z]{3,}", s.lower())}
    backed |= set(re.findall(r"[a-zA-Z]{3,}", candidate.field.lower()))
    flagged: list[str] = []
    # Capture up to ~3 words after "experience with/in" so adjacent claims stay separate.
    pattern = r"experience (?:with|in) ([a-zA-Z][a-zA-Z\-]*(?:\s+[a-zA-Z\-]+){0,2})"
    for claim in re.findall(pattern, letter, re.I):
        claim_tokens = set(re.findall(r"[a-zA-Z]{3,}", claim.lower()))
        if claim_tokens and not (claim_tokens & backed):
            flagged.append(claim.strip())
    return flagged
