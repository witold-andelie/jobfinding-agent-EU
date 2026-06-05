"""Scrapling-backed crawler fetcher — drop-in for CareerPageCrawler, offline.

Scrapling itself is an optional dependency and is NOT installed in CI; the fetch is
an injected seam, so these tests never import scrapling or hit the network.
"""

from job_agent.models.company import CompanyTarget
from job_agent.sources.crawl import (
    CareerPageCrawler,
    ScraplingFetcher,
    build_career_crawler,
    scrapling_available,
)


class _FakePage:
    def __init__(self, html: str) -> None:
        self.html_content = html


def test_fetcher_returns_html_and_passes_options() -> None:
    seen = {}

    def fake_fetch(url, **opts):
        seen["url"], seen["opts"] = url, opts
        return _FakePage("<html>open roles</html>")

    fetcher = ScraplingFetcher(fetch_fn=fake_fetch, solve_cloudflare=True,
                               additional_args={"ignore_https_errors": True})
    assert fetcher("https://acme.cz/careers") == "<html>open roles</html>"
    assert seen["url"] == "https://acme.cz/careers"
    assert seen["opts"]["solve_cloudflare"] is True and seen["opts"]["headless"] is True
    assert seen["opts"]["additional_args"] == {"ignore_https_errors": True}  # extra opts pass through


def test_scrapling_backed_crawler_extracts_jobs() -> None:
    # The whole point: a Scrapling fetcher slots into the existing CareerPageCrawler.
    pages = {
        "https://acme.cz": '<a href="/kariera">Kariéra</a>',
        "https://acme.cz/kariera": '<a href="/job/1">Senior Engineer</a>',
    }
    fetcher = ScraplingFetcher(fetch_fn=lambda url, **o: _FakePage(pages[url]))
    crawler = CareerPageCrawler(fetcher)

    jobs = crawler.crawl(CompanyTarget(name="Acme", country="CZ", website="https://acme.cz"))
    assert [j.title for j in jobs] == ["Senior Engineer"]


def test_build_career_crawler_returns_usable_crawler() -> None:
    # Works whether or not scrapling is installed (Scrapling backend vs static fallback).
    assert isinstance(scrapling_available(), bool)
    crawler = build_career_crawler()
    assert isinstance(crawler, CareerPageCrawler)


def test_build_career_crawler_accepts_explicit_http_get() -> None:
    crawler = build_career_crawler(http_get=lambda url: "<html></html>")
    assert isinstance(crawler, CareerPageCrawler)
