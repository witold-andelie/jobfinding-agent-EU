"""Search-driven ATS discovery — find hiring companies with no names known, offline."""

from job_agent.discovery import AtsSearchDiscoverer, DiscoveryQuery, keep_jobs_in_country
from job_agent.models.company import ATSPlatform
from job_agent.models.job import Job


def test_discovers_tenants_from_search_results() -> None:
    # The search engine returns ATS board URLs; we extract handles → CompanyTargets.
    results = {
        "site:jobs.personio.de praha": [
            "https://acme.jobs.personio.de/job/1", "https://bravo.jobs.personio.de/",
            "https://acme.jobs.personio.de/job/2",  # duplicate handle
        ],
        "site:jobs.lever.co praha": ["https://jobs.lever.co/charlie/x", "https://google.com/notats"],
        "site:boards.greenhouse.io praha": ["https://boards.greenhouse.io/delta/jobs/9"],
        "site:recruitee.com praha": [],
    }
    discoverer = AtsSearchDiscoverer(lambda q: results.get(q, []))

    companies = discoverer.discover(DiscoveryQuery(country="CZ"))
    handles = {(c.ats, c.ats_handle) for c in companies}
    assert handles == {
        (ATSPlatform.personio, "acme"), (ATSPlatform.personio, "bravo"),
        (ATSPlatform.lever, "charlie"), (ATSPlatform.greenhouse, "delta"),
    }
    assert all(c.discovered_via == "ats_search" for c in companies)


def test_query_targets_country_location() -> None:
    seen = []
    AtsSearchDiscoverer(lambda q: seen.append(q) or []).discover(
        DiscoveryQuery(country="CZ", keywords=["developer"])
    )
    assert any("site:jobs.personio.de praha developer" == q for q in seen)


def test_keep_jobs_in_country_filters_by_city() -> None:
    jobs = [
        Job(source="personio", external_id="1", title="Dev", company="X", country="", city="Prague"),
        Job(source="personio", external_id="2", title="Dev", company="X", country="", city="Berlin",
            description="We also have a Czech office."),  # mention must NOT leak it in
        Job(source="personio", external_id="3", title="Dev", company="X", country="",
            city="Remote (Czech Republic)"),
        Job(source="personio", external_id="4", title="Dev", company="X", country="", city="Brno"),
    ]
    cz = keep_jobs_in_country(jobs, "CZ")
    assert {j.external_id for j in cz} == {"1", "3", "4"}  # Berlin dropped despite the mention
