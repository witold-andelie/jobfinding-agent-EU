"""LLM gap analysis (DeepSeek chat) — how well a candidate fits a specific job.

Per-job and on-demand (not part of bulk ranking, to bound cost): given a candidate
and one job, DeepSeek returns matched vs missing skills and what to emphasise in
the application. Network lives entirely in the injected ``ask`` seam, so this is
unit-testable offline with a fake ``ask``.
"""

from __future__ import annotations

import json
import re
from dataclasses import dataclass, field

from job_agent.models.candidate import CandidateProfile
from job_agent.models.job import Job

_PROMPT = (
    "You assess how well a candidate fits one job. Be concrete and honest; do NOT "
    "invent experience the candidate lacks.\n"
    "Candidate field: {field}\nCandidate skills: {skills}\n"
    "Job title: {title}\nJob description: {description}\n\n"
    "Reply with ONLY JSON: {{"
    '"matched": ["skills the candidate already has that the job wants"], '
    '"missing": ["skills the job wants that the candidate lacks"], '
    '"emphasis": ["what the candidate should emphasise in the application"], '
    '"summary": "<one-sentence honest fit assessment>"}}.'
)


@dataclass
class GapAnalysis:
    matched: list[str] = field(default_factory=list)
    missing: list[str] = field(default_factory=list)
    emphasis: list[str] = field(default_factory=list)
    summary: str = ""


def analyze_gap(candidate: CandidateProfile, job: Job, ask) -> GapAnalysis:  # ask: Callable[[str], str]
    """Run DeepSeek gap analysis for ``(candidate, job)``; degrades to empty on bad output."""
    prompt = _PROMPT.format(
        field=candidate.field or "(unspecified)",
        skills=", ".join(candidate.skills) or "(none listed)",
        title=job.title,
        description=(job.description or "")[:4000],
    )
    raw = ask(prompt)
    match = re.search(r"\{.*\}", raw, re.DOTALL)
    if not match:
        return GapAnalysis(summary="(no analysis available)")
    try:
        data = json.loads(match.group(0))
    except json.JSONDecodeError:
        return GapAnalysis(summary="(unparseable analysis)")
    return GapAnalysis(
        matched=list(data.get("matched", [])),
        missing=list(data.get("missing", [])),
        emphasis=list(data.get("emphasis", [])),
        summary=str(data.get("summary", "")),
    )
