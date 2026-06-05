"""RobotsTxtChecker — real robots.txt compliance (fixture is jobup.ch's actual file)."""

from job_agent.sources.crawl import RobotsTxtChecker

# Verbatim from jobup.ch/robots.txt (probed 2026): the /api/ disallow is why we
# must NOT use its JSON endpoint.
_JOBUP_ROBOTS = """User-agent: *
Disallow: /*?*feat=
Disallow: /external/
Disallow: /api/
Disallow: /api_proxy/
Disallow: /de/login/
"""


def test_respects_disallowed_api_path() -> None:
    calls: list[str] = []

    def fetch(url: str) -> str:
        calls.append(url)
        return _JOBUP_ROBOTS

    checker = RobotsTxtChecker(fetch)
    assert checker.allowed("https://www.jobup.ch/fr/emplois/detail/abc/") is True
    assert checker.allowed("https://www.jobup.ch/api/v1/public/search") is False
    assert checker.allowed("https://www.jobup.ch/fr/emplois/x/") is True  # cached
    assert len(calls) == 1  # robots.txt fetched once per host


def test_missing_robots_allows_all() -> None:
    def boom(url: str) -> str:
        raise RuntimeError("404")

    assert RobotsTxtChecker(boom).allowed("https://x.ch/api/anything") is True
