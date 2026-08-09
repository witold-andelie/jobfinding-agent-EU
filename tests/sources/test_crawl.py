"""Career-page crawler: find careers link, extract jobs, ATS hand-off, robots gate."""

from job_agent.models.company import CompanyTarget
from job_agent.sources.crawl import CareerPageCrawler, extract_jobs, find_careers_url

_HOME = '<html><nav><a href="/kariera">Kariéra</a><a href="/about">About</a></nav></html>'
_CAREERS_PLAIN = ('<ul><a href="/job/123">Senior Engineer</a>'
                  '<a href="/job/124">Junior Analyst</a><a href="/contact">Contact</a></ul>')
_CAREERS_ATS = '<html>Apply at <a href="https://acme.jobs.personio.de/">our board</a></html>'
_CAREERS_WORKDAY = '<html>Apply at <a href="https://bobcat.wd1.myworkdayjobs.com/en-US/BobcatExternal">our board</a></html>'
_PERSONIO = '<?xml version="1.0"?><workzag-jobs><position><id>9</id><name>DevOps</name></position></workzag-jobs>'
_WORKDAY = '{"jobPostings":[{"title":"Assembly Planner","locationsText":"Czech Republic, Dobris","externalPath":"/job/CZ/Assembly-Planner_JR1"}]}'
_DETAIL = '<html><h1>Remote Service Trainer for German market</h1><p>Dobris, Czech Republic</p></html>'


def _router(rules):
    def _get(url):
        for needle, body in rules:
            if needle in url:
                return body
        raise AssertionError(f"unexpected fetch: {url}")
    return _get


def test_find_careers_url_resolves_absolute() -> None:
    assert find_careers_url(_HOME, "https://acme.cz") == "https://acme.cz/kariera"
    assert find_careers_url("<a href='/about'>About</a>", "https://x.cz") is None


def test_extract_jobs_from_plain_html() -> None:
    company = CompanyTarget(name="Acme", country="CZ", website="https://acme.cz")
    jobs = extract_jobs(_CAREERS_PLAIN, company, "https://acme.cz/kariera")
    assert {j.title for j in jobs} == {"Senior Engineer", "Junior Analyst"}  # Contact skipped
    assert all(j.source == "careerpage" and j.country == "CZ" for j in jobs)


def test_crawler_extracts_from_plain_careers_page() -> None:
    company = CompanyTarget(name="Acme", country="CZ", website="https://acme.cz")
    http = _router([("/kariera", _CAREERS_PLAIN), ("acme.cz", _HOME)])
    jobs = CareerPageCrawler(http).crawl(company)
    assert len(jobs) == 2


def test_crawler_hands_off_to_ats_when_detected() -> None:
    company = CompanyTarget(name="Acme", country="CZ", website="https://acme.cz")
    http = _router([("personio.de/xml", _PERSONIO), ("/kariera", _CAREERS_ATS), ("acme.cz", _HOME)])
    jobs = CareerPageCrawler(http).crawl(company)
    # Detected Personio handle "acme" → structured ATS feed, not HTML scraping.
    assert [j.source for j in jobs] == ["personio"]
    assert jobs[0].title == "DevOps"


def test_crawler_hands_off_to_workday_post_feed() -> None:
    company = CompanyTarget(name="Bobcat", country="CZ", website="https://bobcat.com")
    http = _router([( "/kariera", _CAREERS_WORKDAY), ("bobcat.com", _HOME)])
    jobs = CareerPageCrawler(http, workday_post=lambda url, body, headers=None: _WORKDAY).crawl(company)
    assert jobs[0].source == "workday"
    assert jobs[0].title == "Assembly Planner"


def test_crawler_uses_search_hit_job_detail_url() -> None:
    company = CompanyTarget(
        name="Bobcat", country="CZ", website="https://jobs.doosan.com",
        careers_url="https://jobs.doosan.com/bobcat/job/Remote-Service-Trainer/123",
        discovered_via="web_search", city_hint="dobříš",
    )
    http = _router([("/bobcat/job/", _DETAIL), ("jobs.doosan.com", _HOME)])
    jobs = CareerPageCrawler(http).crawl(company)
    assert jobs[0].title == "Remote Service Trainer for German market"
    assert jobs[0].city == "dobříš"


def test_crawler_respects_robots_disallow() -> None:
    class DenyAll:
        def allowed(self, url): return False

    company = CompanyTarget(name="Acme", country="CZ", website="https://acme.cz")
    jobs = CareerPageCrawler(lambda u: _HOME, robots=DenyAll()).crawl(company)
    assert jobs == []


def test_crawler_no_website_returns_empty() -> None:
    assert CareerPageCrawler(lambda u: _HOME).crawl(CompanyTarget(name="X", country="CZ")) == []
