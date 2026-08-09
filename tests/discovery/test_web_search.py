from job_agent.discovery import CareerWebDiscoverer, DiscoveryQuery


def test_discovers_company_domains_and_excludes_job_portals() -> None:
    results = {
        "praha (careers OR jobs OR hiring)": [
            "https://careers.example-manufacturing.cz/jobs/engineer",
            "https://www.linkedin.com/jobs/view/1",
            "https://boards.greenhouse.io/acme/jobs/2",
        ]
    }
    found = CareerWebDiscoverer(lambda q: results.get(q, []), cities=1).discover(
        DiscoveryQuery(country="CZ")
    )

    assert len(found) == 1
    assert found[0].website == "https://careers.example-manufacturing.cz"
    assert found[0].city_hint == "praha"
    assert found[0].discovered_via == "web_search"


def test_discovers_registered_company_owned_career_host() -> None:
    def search(query: str) -> list[str]:
        if query == "site:jobs.doosan.com praha":
            return ["https://jobs.doosan.com/bobcat/job/Service-Trainer/123"]
        return []

    found = CareerWebDiscoverer(search, cities=1).discover(DiscoveryQuery(country="CZ"))

    bobcat = next(c for c in found if c.website == "https://jobs.doosan.com")
    assert bobcat.name == "Doosan Bobcat"
    assert bobcat.careers_url.endswith("/Service-Trainer/123")
