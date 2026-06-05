"""CV variant — skill re-ranking (offline), summary grounding, .docx export."""

import pytest

from job_agent.models.job import Job
from job_agent.parsing.cv import ParsedCV
from job_agent.writing import generate_cv_variant, rank_skills, tailored_summary

_JOB = Job(source="s", external_id="42", title="Public Affairs Officer", company="Rhône SA",
           country="CH", description="Advocacy, stakeholder engagement, and policy analysis.")
_PARSED = ParsedCV(
    name="Mei Lin Zhang", contact="mei@example.com",
    field="international relations",
    skills=["python", "advocacy", "report writing", "policy analysis"],
    languages=["en", "fr"], years_experience=1.0,
    experience=["Research assistant, Geneva NGO — drafted policy briefs (2023–2024)"],
    education=["MA International Relations, Graduate Institute Geneva"],
)


def test_rank_skills_puts_relevant_first_without_inventing() -> None:
    ranked = rank_skills(_PARSED.skills, _JOB, matched=["policy analysis"])
    assert ranked[0] == "policy analysis"          # gap-matched → first
    assert ranked.index("advocacy") < ranked.index("python")  # job-overlap beats unrelated
    assert sorted(ranked) == sorted(_PARSED.skills)  # same set, nothing added/dropped


def test_tailored_summary_is_grounded() -> None:
    seen = {}
    out = tailored_summary(_PARSED, _JOB,
                           ask=lambda p: seen.setdefault("p", p) and "" or "Tailored summary.")
    assert out == "Tailored summary."
    assert "do NOT invent" in seen["p"] and "international relations" in seen["p"]


def test_generate_cv_variant_writes_docx(tmp_path) -> None:
    pytest.importorskip("docx")
    from docx import Document

    path = generate_cv_variant(_PARSED, _JOB, ask=lambda p: "A targeted profile summary.",
                               artifacts_dir=tmp_path, matched=["advocacy"])
    assert path.exists() and path.name == "CV_rhone-sa_42.docx"

    texts = [p.text for p in Document(str(path)).paragraphs]
    assert "Mei Lin Zhang" in texts
    assert "A targeted profile summary." in texts
    assert "advocacy" in texts  # re-ranked skill present
    # experience carried over verbatim
    assert any("Research assistant, Geneva NGO" in t for t in texts)
