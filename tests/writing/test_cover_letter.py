"""Cover-letter generation (DeepSeek) — grounding, emphasis, anti-fabrication check."""

from job_agent.models.candidate import CandidateProfile
from job_agent.models.job import Job
from job_agent.writing import generate_cover_letter, unsupported_claims

_CAND = CandidateProfile(nationality="CN", field="international relations",
                         skills=["policy analysis", "advocacy"], languages=["en", "fr"],
                         years_experience=1.0)
_JOB = Job(source="s", external_id="1", title="Public Affairs Officer",
           company="Rhône SA", country="CH", city="Geneva",
           description="Advocacy and stakeholder engagement.")


def test_prompt_is_grounded_and_carries_emphasis() -> None:
    seen = {}
    generate_cover_letter(_CAND, _JOB, ask=lambda p: seen.setdefault("p", p) and "" or "Dear...",
                          emphasis=["French language skills"])
    p = seen["p"]
    assert "do NOT invent" in p
    assert "international relations" in p and "Public Affairs Officer" in p
    assert "Emphasise: French language skills" in p


def test_returns_stripped_letter() -> None:
    letter = generate_cover_letter(_CAND, _JOB, ask=lambda p: "  Dear Hiring Manager... \n ")
    assert letter == "Dear Hiring Manager..."


def test_language_parameter_flows_into_prompt() -> None:
    seen = {}
    generate_cover_letter(_CAND, _JOB, ask=lambda p: seen.setdefault("p", p) and "" or "x",
                          language="French")
    assert "Write in French" in seen["p"]


def test_unsupported_claims_flags_fabrication() -> None:
    # "experience with machine learning" is not backed by her policy/advocacy profile.
    letter = ("I have experience in policy analysis and experience with machine learning "
              "that suits this role.")
    flagged = unsupported_claims(letter, _CAND)
    assert any("machine learning" in f for f in flagged)
    assert not any("policy" in f for f in flagged)  # policy analysis IS backed


def test_unsupported_claims_clean_letter() -> None:
    assert unsupported_claims("I bring experience in advocacy and policy analysis.", _CAND) == []
