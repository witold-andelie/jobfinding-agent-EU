from job_agent.models.company import ATSPlatform, CompanyTarget
from job_agent.sources.ats import ADAPTERS


def _company(platform: ATSPlatform) -> CompanyTarget:
    return CompanyTarget(name="Acme", country="CZ", ats=platform, ats_handle="acme")


def test_ashby_adapter_parses_public_board() -> None:
    jobs = ADAPTERS[ATSPlatform.ashby].parse(
        '{"jobs":[{"id":"a1","title":"Operations Specialist",'
        '"location":"Prague","jobUrl":"https://jobs.ashbyhq.com/acme/a1"}]}',
        _company(ATSPlatform.ashby),
    )
    assert jobs[0].source == "ashby"
    assert jobs[0].city == "Prague"


def test_smartrecruiters_adapter_parses_public_board() -> None:
    jobs = ADAPTERS[ATSPlatform.smartrecruiters].parse(
        '{"content":[{"id":"s1","name":"Plant Controller",'
        '"location":{"city":"Brno"},"ref":"https://jobs.example/s1"}]}',
        _company(ATSPlatform.smartrecruiters),
    )
    assert jobs[0].title == "Plant Controller"
    assert jobs[0].city == "Brno"
