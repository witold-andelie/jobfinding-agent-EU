"""LLM gap analysis (DeepSeek) — parsing + DI seam, offline."""

from job_agent.matching import analyze_gap
from job_agent.models.candidate import CandidateProfile
from job_agent.models.job import Job

_CAND = CandidateProfile(nationality="IN", field="data science", skills=["python", "sql"])
_JOB = Job(source="s", external_id="1", title="ML Engineer", company="C", country="DE",
           description="We want python, sql, and PyTorch experience.")


def test_analyze_gap_parses_json() -> None:
    reply = ('Here you go: {"matched": ["python", "sql"], "missing": ["pytorch"], '
             '"emphasis": ["highlight SQL projects"], "summary": "Strong fit, missing PyTorch."}')
    gap = analyze_gap(_CAND, _JOB, ask=lambda prompt: reply)
    assert gap.matched == ["python", "sql"]
    assert gap.missing == ["pytorch"]
    assert "PyTorch" in gap.summary


def test_analyze_gap_prompt_includes_candidate_and_job() -> None:
    seen = {}
    analyze_gap(_CAND, _JOB, ask=lambda p: seen.setdefault("p", p) and "" or '{"summary":"x"}')
    # ensure the prompt carries the real context (and the no-fabrication instruction)
    assert "data science" in seen["p"] and "ML Engineer" in seen["p"]
    assert "do NOT" in seen["p"]


def test_analyze_gap_degrades_on_garbage() -> None:
    gap = analyze_gap(_CAND, _JOB, ask=lambda prompt: "sorry, no")
    assert gap.matched == [] and "no analysis" in gap.summary
