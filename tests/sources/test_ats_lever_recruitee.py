"""Lever + Recruitee ATS adapters — built to the live API shapes, offline."""

from job_agent.models.company import ATSPlatform, CompanyTarget
from job_agent.models.job import EmploymentType
from job_agent.sources import fetch_company_jobs

# Lever: top-level array (verified shape from api.lever.co/v0/postings/{h}?mode=json).
_LEVER = """[
  {"id": "abc-1", "text": "Senior Backend Engineer",
   "categories": {"location": "Praha", "commitment": "Full-time", "team": "Eng"},
   "hostedUrl": "https://jobs.lever.co/acme/abc-1", "descriptionPlain": "Build APIs.", "country": "CZ"},
  {"id": "abc-2", "text": "Marketing Intern",
   "categories": {"location": "Wien", "commitment": "Internship"},
   "hostedUrl": "https://jobs.lever.co/acme/abc-2", "descriptionPlain": "Learn."}
]"""

# Recruitee: {"offers": [...]} (verified envelope from {h}.recruitee.com/api/offers/).
_RECRUITEE = """{"offers": [
  {"id": 42, "title": "Junior Data Analyst", "city": "Geneva",
   "careers_url": "https://acme.recruitee.com/o/junior-data-analyst",
   "description": "Analyse data.", "employment_type_code": "fulltime"}
]}"""


def _http(mapping):
    def _get(url):
        for needle, body in mapping.items():
            if needle in url:
                return body
        raise AssertionError(f"unexpected fetch: {url}")
    return _get


def test_lever_adapter_parses_postings() -> None:
    company = CompanyTarget(name="Acme", country="CZ", ats=ATSPlatform.lever, ats_handle="acme")
    jobs = fetch_company_jobs(company, _http({"api.lever.co/v0/postings/acme": _LEVER}))

    assert [j.external_id for j in jobs] == ["abc-1", "abc-2"]
    assert jobs[0].source == "lever" and jobs[0].city == "Praha" and jobs[0].country == "CZ"
    assert jobs[0].url == "https://jobs.lever.co/acme/abc-1"
    assert jobs[1].employment_type is EmploymentType.internship  # from title + commitment


def test_recruitee_adapter_parses_offers() -> None:
    company = CompanyTarget(name="Acme", country="CH", ats=ATSPlatform.recruitee, ats_handle="acme")
    jobs = fetch_company_jobs(company, _http({"acme.recruitee.com/api/offers": _RECRUITEE}))

    assert len(jobs) == 1
    assert jobs[0].source == "recruitee" and jobs[0].external_id == "42"
    assert jobs[0].city == "Geneva" and jobs[0].country == "CH"
    assert jobs[0].url == "https://acme.recruitee.com/o/junior-data-analyst"


def test_new_adapters_registered() -> None:
    from job_agent.sources.ats import ADAPTERS
    assert {ATSPlatform.personio, ATSPlatform.greenhouse, ATSPlatform.lever,
            ATSPlatform.recruitee} <= set(ADAPTERS)
