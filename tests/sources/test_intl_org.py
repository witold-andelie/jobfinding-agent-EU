"""Track B — international-organisation source (ReliefWeb), offline."""

from job_agent.models.candidate import Track
from job_agent.models.job import EmploymentType
from job_agent.sources.intl_org import fetch_intl_org_jobs

# Real-shaped ReliefWeb /v1/jobs response for Geneva-based UN/NGO roles.
RELIEFWEB_JSON = """
{"data": [
  {"id": "999001", "fields": {
     "title": "Junior Programme Officer", "city": "Geneva",
     "source": [{"name": "UNHCR"}], "country": [{"name": "Switzerland", "iso3": "che"}],
     "type": [{"name": "Job"}], "url": "https://reliefweb.int/job/999001", "body": "..."}},
  {"id": "999002", "fields": {
     "title": "Communications Internship", "city": "Geneva",
     "source": [{"name": "WHO"}], "country": [{"name": "Switzerland", "iso3": "che"}],
     "type": [{"name": "Internship"}], "url": "https://reliefweb.int/job/999002", "body": "..."}}
]}"""


def test_reliefweb_geneva_jobs_tagged_track_b() -> None:
    jobs = fetch_intl_org_jobs("CHE", http_get=lambda url: RELIEFWEB_JSON)

    assert len(jobs) == 2
    assert all(j.track is Track.intl_org for j in jobs)
    assert all(j.country == "CH" for j in jobs)
    assert jobs[0].company == "UNHCR"
    assert jobs[0].city == "Geneva"
    assert jobs[1].employment_type is EmploymentType.internship
