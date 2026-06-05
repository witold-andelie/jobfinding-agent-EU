"""SearchDomainResolver — Brave resolution, name guard, caching, quota budget (offline)."""

from job_agent.discovery import FileCache, SearchDomainResolver
from job_agent.models.company import CompanyTarget

_BRAVE = """{"web": {"results": [
  {"url": "https://www.linkedin.com/company/acme", "title": "Acme | LinkedIn"},
  {"url": "https://jobs.cz/acme", "title": "Acme jobs"},
  {"url": "https://www.acme-software.cz/", "title": "Acme Software"}
]}}"""

_company = CompanyTarget(name="Acme Software s.r.o.", country="CZ")


class _CountingHttp:
    def __init__(self, body: str) -> None:
        self.body = body
        self.calls = 0

    def __call__(self, url, headers=None):
        self.calls += 1
        return self.body


def test_resolves_company_site_skipping_aggregators() -> None:
    http = _CountingHttp(_BRAVE)
    assert SearchDomainResolver(http, token="tok").resolve(_company) == "https://acme-software.cz"


def test_name_guard_rejects_unrelated_domain() -> None:
    # Distinctive token "bitsafe" is absent from the result host → don't crawl a
    # same-named-but-unrelated company; return None.
    brave = '{"web": {"results": [{"url": "https://randomcorp.com/"}]}}'
    company = CompanyTarget(name="Bitsafe Software s.r.o.", country="CZ")
    assert SearchDomainResolver(lambda u, h=None: brave, token="t").resolve(company) is None


def test_cache_prevents_second_brave_call() -> None:
    http = _CountingHttp(_BRAVE)
    r = SearchDomainResolver(http, token="t")
    r.resolve(_company)
    r.resolve(_company)  # same company again
    assert http.calls == 1 and r.calls_made == 1  # second hit served from cache


def test_negative_results_are_cached() -> None:
    http = _CountingHttp('{"web": {"results": [{"url": "https://linkedin.com/x"}]}}')
    r = SearchDomainResolver(http, token="t")
    assert r.resolve(_company) is None
    assert r.resolve(_company) is None
    assert http.calls == 1  # the None was cached, not re-queried


def test_budget_guard_stops_live_calls() -> None:
    http = _CountingHttp(_BRAVE)
    r = SearchDomainResolver(http, token="t", max_calls=1)
    r.resolve(CompanyTarget(name="Alpha Bravo", country="CZ"))
    r.resolve(CompanyTarget(name="Charlie Delta", country="CZ"))  # over budget
    assert http.calls == 1 and r.calls_made == 1


def test_file_cache_persists(tmp_path) -> None:
    path = tmp_path / "cache.json"
    http = _CountingHttp(_BRAVE)
    SearchDomainResolver(http, token="t", cache=FileCache(path)).resolve(_company)
    # A fresh resolver with the same file must not call Brave again.
    r2 = SearchDomainResolver(http, token="t", cache=FileCache(path))
    assert r2.resolve(_company) == "https://acme-software.cz"
    assert http.calls == 1  # served from the persisted cache
