"""Offline tests for the ATS adapter layer — the SME long-tail coverage path.

No network: ``fetch_company_jobs`` takes an injected ``http_get`` that returns
fixture strings keyed by URL. This is exactly how Scout will run in tests.
"""

from job_agent.models.company import ATSPlatform, CompanyTarget
from job_agent.models.job import EmploymentType
from job_agent.sources import fetch_company_jobs

# A trimmed but real-shaped Personio XML feed (DACH SME, e.g. a Mittelstand firm).
PERSONIO_XML = """<?xml version="1.0" encoding="utf-8"?>
<workzag-jobs>
  <position>
    <id>101</id>
    <name>Junior Mechanical Engineer (m/f/d)</name>
    <office>Dobris</office>
    <department>Engineering</department>
    <employmentType>permanent</employmentType>
    <jobDescriptions>
      <jobDescription><name>Tasks</name><value>Design hydraulic systems.</value></jobDescription>
    </jobDescriptions>
  </position>
  <position>
    <id>102</id>
    <name>Praktikum Marketing</name>
    <office>Wien</office>
    <department>Marketing</department>
    <employmentType>intern</employmentType>
    <jobDescriptions>
      <jobDescription><name>Profil</name><value>Studium im Bereich Marketing.</value></jobDescription>
    </jobDescriptions>
  </position>
</workzag-jobs>"""

GREENHOUSE_JSON = """
{"jobs": [
  {"id": 4567, "title": "Backend Engineer", "absolute_url": "https://acme.com/jobs/4567",
   "location": {"name": "Berlin, Germany"}, "content": "Build APIs."},
  {"id": 4568, "title": "Software Engineering Intern", "absolute_url": "https://acme.com/jobs/4568",
   "location": {"name": "Remote"}, "content": "Learn and ship."}
]}"""


def _fake_http(mapping: dict[str, str]):
    def _get(url: str) -> str:
        return mapping[url]

    return _get


def test_personio_feed_parsed_into_jobs() -> None:
    company = CompanyTarget(
        name="Mittelstand Maschinenbau GmbH",
        country="CZ",
        ats=ATSPlatform.personio,
        ats_handle="mittelstand",
    )
    http = _fake_http({"https://mittelstand.jobs.personio.de/xml": PERSONIO_XML})

    jobs = fetch_company_jobs(company, http)

    assert len(jobs) == 2
    first = jobs[0]
    assert first.source == "personio"
    assert first.external_id == "101"
    assert first.company == "Mittelstand Maschinenbau GmbH"
    assert first.country == "CZ"
    assert first.city == "Dobris"
    assert first.url == "https://mittelstand.jobs.personio.de/job/101"
    # Praktikum → internship, classified multilingually.
    assert jobs[1].employment_type is EmploymentType.internship


def test_greenhouse_feed_parsed_into_jobs() -> None:
    company = CompanyTarget(
        name="Acme Scaleup",
        country="DE",
        ats=ATSPlatform.greenhouse,
        ats_handle="acme",
    )
    url = "https://boards-api.greenhouse.io/v1/boards/acme/jobs?content=true"
    jobs = fetch_company_jobs(company, _fake_http({url: GREENHOUSE_JSON}))

    assert [j.external_id for j in jobs] == ["4567", "4568"]
    assert jobs[0].city == "Berlin, Germany"
    assert jobs[1].employment_type is EmploymentType.internship


def test_company_without_ats_yields_no_jobs_and_no_network() -> None:
    # unknown ATS → empty list, http_get never called (would KeyError if it were).
    company = CompanyTarget(name="Bespoke Careers Page Ltd", country="FR")
    jobs = fetch_company_jobs(company, _fake_http({}))
    assert jobs == []
