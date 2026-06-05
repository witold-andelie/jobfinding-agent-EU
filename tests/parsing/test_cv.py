"""CV parsing (DeepSeek) — parsing, normalisation, and profile merge, offline."""

from job_agent.models.candidate import Track
from job_agent.parsing import parse_cv, to_profile

_REPLY = ('{"field": "international relations", "skills": ["policy analysis", "advocacy"], '
          '"languages": ["EN", "FR"], "years_experience": 1.5, "degree_country": "ch", '
          '"summary": "Geneva IR graduate."}')


def test_parse_cv_extracts_and_normalises() -> None:
    parsed = parse_cv("...cv text...", ask=lambda prompt: _REPLY)
    assert parsed.field == "international relations"
    assert parsed.skills == ["policy analysis", "advocacy"]
    assert parsed.languages == ["en", "fr"]          # lowercased
    assert parsed.years_experience == 1.5
    assert parsed.degree_country == "CH"             # 2-letter, uppercased


def test_prompt_forbids_fabrication_and_truncates() -> None:
    seen = {}
    parse_cv("x" * 9000, ask=lambda p: seen.setdefault("p", p) and "" or _REPLY)
    assert "Do NOT invent" in seen["p"]
    assert len(seen["p"]) < 8600  # CV truncated to ~8000 chars


def test_to_profile_merges_nationality_kept_separate() -> None:
    parsed = parse_cv("...", ask=lambda prompt: _REPLY)
    profile = to_profile(parsed, nationality="CN", tracks=[Track.private, Track.intl_org])
    assert profile.nationality == "CN"               # supplied, not from CV
    assert profile.degree_country == "CH"            # from CV
    assert profile.field == "international relations"
    assert profile.skills == ["policy analysis", "advocacy"]


def test_degree_country_override() -> None:
    parsed = parse_cv("...", ask=lambda prompt: _REPLY)
    profile = to_profile(parsed, nationality="CN", degree_country="DE")
    assert profile.degree_country == "DE"            # user override wins


def test_parse_cv_degrades_on_garbage() -> None:
    parsed = parse_cv("...", ask=lambda prompt: "I can't do that")
    assert parsed.skills == [] and "could not parse" in parsed.summary
