"""End-to-end demos: discovery -> ATS/intl-org fetch -> visa feasibility.

Two real-world verticals, fully offline:
- Czech IT SME (Track A) — local Czech degree removes sponsorship entirely.
- Geneva International Relations graduate (Track A Swiss industries + Track B
  international organisations) — a Swiss degree unlocks the private market, and
  international organisations bypass the work permit altogether.
"""

from job_agent.data.example_seeds import CZECH_IT_SEEDS, SWISS_SEEDS
from job_agent.discovery import DiscoveryQuery, SeedDiscoverer
from job_agent.models.candidate import CandidateProfile, Track
from job_agent.models.company import CompanyTarget
from job_agent.sources import fetch_company_jobs
from job_agent.sources.intl_org import fetch_intl_org_jobs
from job_agent.visa import FeasibilityLevel, assess

# --- fixtures (what each ATS / API would return) -----------------------------

_PERSONIO_PUBLIC_AFFAIRS = """<?xml version="1.0" encoding="utf-8"?>
<workzag-jobs>
  <position>
    <id>501</id>
    <name>Junior Public Affairs Officer (m/f/d)</name>
    <office>Geneva</office>
    <employmentType>permanent</employmentType>
    <jobDescriptions><jobDescription><name>Role</name>
      <value>Support advocacy and stakeholder engagement.</value></jobDescription></jobDescriptions>
  </position>
</workzag-jobs>"""

_PERSONIO_CZ_IT = """<?xml version="1.0" encoding="utf-8"?>
<workzag-jobs>
  <position><id>201</id><name>Junior Backend Developer</name><office>Prague</office>
    <employmentType>permanent</employmentType></position>
</workzag-jobs>"""

_RELIEFWEB_GENEVA = """
{"data": [
  {"id": "999001", "fields": {
     "title": "Junior Programme Officer", "city": "Geneva",
     "source": [{"name": "UNHCR"}], "country": [{"name": "Switzerland", "iso3": "che"}],
     "type": [{"name": "Job"}], "url": "https://reliefweb.int/job/999001", "body": "..."}}
]}"""


def _http(mapping: dict[str, str]):
    return lambda url: mapping[url]


# --- Demo 1: Czech IT SME, non-EU candidate with a Czech degree ---------------


def test_demo_czech_it_local_degree_no_sponsorship() -> None:
    candidate = CandidateProfile(nationality="IN", degree_country="CZ", field="software")

    # Discover Czech IT companies, fetch one with a known ATS, assess feasibility.
    companies = SeedDiscoverer(CZECH_IT_SEEDS).discover(
        DiscoveryQuery(country="CZ", industry="IT")
    )
    vltava = next(c for c in companies if c.ats_handle == "vltavasoftware")
    jobs = fetch_company_jobs(
        vltava, _http({"https://vltavasoftware.jobs.personio.de/xml": _PERSONIO_CZ_IT})
    )

    assert jobs and jobs[0].title == "Junior Backend Developer"
    result = assess(candidate, jobs[0])
    assert result.level is FeasibilityLevel.green
    assert result.needs_employer_sponsorship is False  # Czech degree = labour-market access
    assert "exemption" in result.path


# --- Demo 2: Geneva IR graduate (the friend) — Swiss degree -------------------


def test_demo_geneva_ir_graduate_both_tracks_viable() -> None:
    # Studying International Relations in Geneva => Swiss degree; non-EU here to show
    # the Swiss-degree unlock (an EU national would simply have free movement).
    friend = CandidateProfile(
        nationality="CN",
        degree_country="CH",
        field="international relations",
        languages=["en", "fr"],
        tracks=[Track.private, Track.intl_org],
    )

    # Track A — a Swiss public-affairs employer (IR-adjacent private market).
    swiss_pa = SeedDiscoverer(SWISS_SEEDS).discover(
        DiscoveryQuery(country="CH", industry="Public Affairs")
    )
    assert swiss_pa, "expected Geneva public-affairs employer in Swiss seeds"
    rhone = swiss_pa[0]
    pa_jobs = fetch_company_jobs(
        rhone, _http({"https://rhonepublicaffairs.jobs.personio.de/xml": _PERSONIO_PUBLIC_AFFAIRS})
    )
    pa_result = assess(friend, pa_jobs[0])
    assert pa_result.level is FeasibilityLevel.green
    assert pa_result.needs_employer_sponsorship is False  # Swiss degree waives priority check

    # Track B — Geneva international organisation (work permit bypassed).
    intl_jobs = fetch_intl_org_jobs("CHE", lambda url: _RELIEFWEB_GENEVA)
    assert intl_jobs[0].track is Track.intl_org
    intl_result = assess(friend, intl_jobs[0])
    assert intl_result.level is FeasibilityLevel.green
    assert "International organisation" in intl_result.path


def test_swiss_seeds_span_multiple_industries() -> None:
    industries = {c.industry for c in SWISS_SEEDS}
    # IR-adjacent and broader sectors both represented.
    assert any("NGO" in (i or "") for i in industries)
    assert any("Finance" in (i or "") for i in industries)
    assert len({c.country for c in SWISS_SEEDS}) == 1  # all CH
