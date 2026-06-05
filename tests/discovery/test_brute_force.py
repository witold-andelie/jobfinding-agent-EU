"""Brute-force pipeline: registry → resolve domain → crawl → jobs (offline)."""

from job_agent.discovery import AresClient, DiscoveryQuery, RegistryDiscoverer
from job_agent.discovery.brute_force import NullResolver, brute_force_search
from job_agent.models.company import CompanyTarget
from job_agent.sources.crawl import CareerPageCrawler

_ARES = """{"ekonomickeSubjekty": [
  {"ico": "1", "obchodniJmeno": "Acme Software s.r.o.", "sidlo": {"nazevObce": "Praha"}}
]}"""
_HOME = '<a href="/kariera">Kariéra</a>'
_CAREERS = '<a href="/job/1">Backend Developer</a>'


def _registry():
    return RegistryDiscoverer([AresClient(lambda url, body, headers=None: _ARES)])


def test_brute_force_resolves_then_crawls() -> None:
    class FixedResolver:
        def resolve(self, company: CompanyTarget) -> str:
            return "https://acme.cz"

    def http(url):
        return _CAREERS if "/kariera" in url else _HOME

    result = brute_force_search(
        DiscoveryQuery(country="CZ", industry="software"),
        registry=_registry(),
        crawler=CareerPageCrawler(http),
        resolver=FixedResolver(),
    )
    assert len(result.companies) == 1
    assert [j.title for j in result.jobs] == ["Backend Developer"]
    assert result.unresolved == [] and result.errors == []


def test_brute_force_without_resolver_reports_unresolved() -> None:
    result = brute_force_search(
        DiscoveryQuery(country="CZ", industry="software"),
        registry=_registry(),
        crawler=CareerPageCrawler(lambda u: _HOME),
        resolver=NullResolver(),
    )
    assert result.jobs == []
    assert result.unresolved == ["Acme Software s.r.o."]  # no website → can't crawl
