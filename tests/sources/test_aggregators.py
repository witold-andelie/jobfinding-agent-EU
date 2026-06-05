"""Layer-1 aggregator board sources (Arbeitsagentur / EURES / Job-Room), offline."""

from job_agent.discovery import DiscoveryQuery
from job_agent.sources.aggregators import ArbeitsagenturSource, EuresSource, JobRoomSource

_ARBEITSAGENTUR = """{"stellenangebote": [
  {"refnr": "X1", "titel": "Junior Data Analyst", "arbeitgeber": "ACME GmbH",
   "arbeitsort": {"ort": "Berlin", "plz": "10115"}},
  {"beruf": "no-id-row"}
]}"""

_EURES = """{"jvs": [
  {"id": "E1", "title": "Junior Consultant", "employer": {"name": "EU Co"},
   "locationMap": {"countryCode": "nl", "city": "Amsterdam"},
   "url": "https://eures/E1", "description": "Great role."}
]}"""

# Real Job-Room shape (probed live): array of jobAdvertisement → jobContent →
# jobDescriptions[].title + company + location.
_JOBROOM = """[
  {"jobAdvertisement": {"id": "J1", "jobContent": {
     "jobDescriptions": [{"title": "Junior Policy Analyst", "description": "Advocacy work."}],
     "company": {"name": "Genève SA", "website": "geneve-sa.ch"},
     "location": {"city": "Genève", "countryIsoCode": "CH"},
     "externalUrl": "https://example.ch/jobs/J1"}}},
  {"jobAdvertisement": {"id": "J2", "jobContent": {
     "jobDescriptions": [{"title": "Pastry Chef"}],
     "company": {"name": "Boulangerie"}, "location": {"city": "Lausanne", "countryIsoCode": "CH"}}}}
]"""


def test_arbeitsagentur_maps_and_skips_idless_rows() -> None:
    src = ArbeitsagenturSource(http=lambda url, headers=None: _ARBEITSAGENTUR)
    jobs = src.fetch(DiscoveryQuery(keywords=["data"]))
    assert len(jobs) == 1  # the no-id row is dropped
    job = jobs[0]
    assert job.source == "arbeitsagentur" and job.country == "DE"
    assert job.external_id == "X1" and job.city == "Berlin"
    assert job.url.endswith("/X1")


def test_eures_spans_countries_and_uppercases_country() -> None:
    src = EuresSource(http=lambda url, headers=None: _EURES)
    jobs = src.fetch(DiscoveryQuery(country="NL", keywords=["consultant"]))
    assert len(jobs) == 1
    assert jobs[0].country == "NL"  # normalised from "nl"
    assert jobs[0].company == "EU Co" and jobs[0].source_type == "eures"


def test_jobroom_swiss_source_posts_and_parses() -> None:
    seen = {}

    def post(url, body, headers=None):
        seen["url"], seen["body"] = url, body
        return _JOBROOM

    src = JobRoomSource(post)
    jobs = src.fetch(DiscoveryQuery(country="CH"))
    assert "_search" in seen["url"] and seen["body"] == {}  # POST with empty body
    assert [j.title for j in jobs] == ["Junior Policy Analyst", "Pastry Chef"]
    assert jobs[0].source == "jobroom" and jobs[0].country == "CH"
    assert jobs[0].company == "Genève SA" and jobs[0].city == "Genève"
    assert jobs[0].url == "https://example.ch/jobs/J1"  # uses externalUrl


def test_jobroom_client_side_keyword_filter() -> None:
    src = JobRoomSource(lambda url, body, headers=None: _JOBROOM)
    jobs = src.fetch(DiscoveryQuery(country="CH", keywords=["policy"]))
    assert [j.title for j in jobs] == ["Junior Policy Analyst"]  # 'Pastry Chef' filtered out
