"""Workday adapter — built to the live CXS POST shape (probed on nvidia), offline."""

from job_agent.models.company import ATSPlatform, CompanyTarget
from job_agent.sources.ats.workday import fetch_workday_jobs, parse_handle

# Shape verified live: POST .../wday/cxs/{tenant}/{site}/jobs → {total, jobPostings:[...]}.
_WORKDAY = """{"total": 2, "jobPostings": [
  {"title": "Senior Manager, Customer Care", "locationsText": "US, CA, Santa Clara",
   "externalPath": "/job/US-CA-Santa-Clara/Senior-Manager--Customer-Care_JR2016464",
   "postedOn": "Posted Today"},
  {"title": "Software Engineering Intern", "locationsText": "Germany, Munich",
   "externalPath": "/job/Germany/Software-Engineering-Intern_JR9999"}
]}"""


def _company() -> CompanyTarget:
    return CompanyTarget(name="NVIDIA", country="DE", ats=ATSPlatform.workday,
                         ats_handle="nvidia|wd5|NVIDIAExternalCareerSite")


def _post(mapping):
    def _p(url, body, headers=None):
        for needle, resp in mapping.items():
            if needle in url:
                return resp
        raise AssertionError(f"unexpected POST: {url}")
    return _p


def test_parse_handle() -> None:
    assert parse_handle("nvidia|wd5|Site") == ("nvidia", "wd5", "Site")
    assert parse_handle("nvidia|wd5") is None  # malformed
    assert parse_handle("") is None


def test_workday_fetch_parses_postings() -> None:
    url = "nvidia.wd5.myworkdayjobs.com/wday/cxs/nvidia/NVIDIAExternalCareerSite/jobs"
    jobs = fetch_workday_jobs(_company(), _post({url: _WORKDAY}))

    assert [j.external_id for j in jobs] == ["JR2016464", "JR9999"]
    assert jobs[0].source == "workday" and jobs[0].country == "DE"
    assert jobs[0].city == "US, CA, Santa Clara"
    assert jobs[0].url.endswith("/NVIDIAExternalCareerSite/job/US-CA-Santa-Clara/"
                                "Senior-Manager--Customer-Care_JR2016464")
    assert jobs[1].employment_type.value == "internship"  # from title


def test_non_workday_or_bad_handle_returns_empty() -> None:
    bad = CompanyTarget(name="X", country="DE", ats=ATSPlatform.workday, ats_handle="only|two")
    assert fetch_workday_jobs(bad, _post({})) == []
    not_wd = CompanyTarget(name="Y", country="DE", ats=ATSPlatform.personio, ats_handle="a|b|c")
    assert fetch_workday_jobs(not_wd, _post({})) == []
