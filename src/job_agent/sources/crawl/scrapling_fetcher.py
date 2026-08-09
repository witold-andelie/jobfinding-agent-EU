"""Scrapling-backed fetcher — a stealth/JS-rendering ``HttpGet`` for the crawler.

The plain static `urllib` fetch misses the SME career pages that are JavaScript-
rendered or block bots with a 403 (seen in the live brute-force run). Scrapling's
``StealthyFetcher`` renders JS and bypasses anti-bot (incl. Cloudflare), so wrapping
it as an ``HttpGet`` (``(url) -> str``) makes it a drop-in for ``CareerPageCrawler``.

Scrapling is an optional dependency (the ``scrape`` extra): the import is lazy and
the fetch call is an injectable seam, so this module imports and unit-tests with no
``scrapling`` installed and zero network.
"""

from __future__ import annotations

import importlib.util
from collections.abc import Callable
from typing import Any

from job_agent.sources import HttpGet
from job_agent.sources.ats.workday import JsonPost
from job_agent.sources.crawl.career_page import CareerPageCrawler, RateLimiter, RobotsChecker


def scrapling_available() -> bool:
    return importlib.util.find_spec("scrapling") is not None


class ScraplingFetcher:
    """An ``HttpGet`` that renders a page via Scrapling and returns its HTML.

    ``stealthy=True`` uses ``StealthyFetcher`` (anti-bot + JS); ``False`` uses
    ``DynamicFetcher`` (plain headless browser). ``fetch_fn`` is an injection seam:
    when omitted, the matching Scrapling fetcher is imported lazily.
    """

    def __init__(
        self,
        *,
        stealthy: bool = True,
        headless: bool = True,
        network_idle: bool = True,
        block_ads: bool = True,
        timeout: int = 30000,
        solve_cloudflare: bool = False,
        fetch_fn: Callable[..., Any] | None = None,
        **extra_opts: Any,
    ) -> None:
        self._stealthy = stealthy
        self._fetch_fn = fetch_fn
        self._opts: dict[str, Any] = {
            "headless": headless,
            "network_idle": network_idle,
            "block_ads": block_ads,
            "timeout": timeout,
        }
        if stealthy:
            self._opts["solve_cloudflare"] = solve_cloudflare
        # Pass-through for proxy, additional_args, useragent, wait_selector, etc.
        self._opts.update(extra_opts)

    def _resolve_fetch(self) -> Callable[..., Any]:
        if self._fetch_fn is not None:
            return self._fetch_fn
        if self._stealthy:
            from scrapling.fetchers import StealthyFetcher  # lazy — optional dependency

            return StealthyFetcher.fetch
        from scrapling.fetchers import DynamicFetcher

        return DynamicFetcher.fetch

    def __call__(self, url: str) -> str:
        page = self._resolve_fetch()(url, **self._opts)
        html = getattr(page, "html_content", None)
        return str(html) if html is not None else str(page)


def build_career_crawler(
    *,
    stealthy: bool = True,
    robots: RobotsChecker | None = None,
    rate_limiter: RateLimiter | None = None,
    http_get: HttpGet | None = None,
    workday_post: JsonPost | None = None,
    **fetch_opts: Any,
) -> CareerPageCrawler:
    """A ``CareerPageCrawler`` using Scrapling when installed, else the static fetch.

    Pass ``http_get`` to force a specific fetcher (e.g. in tests). Otherwise Scrapling
    is used if available; if not, it falls back to the stdlib ``urllib_http`` static
    fetch (which still works for plain HTML pages).
    """
    if http_get is None:
        if scrapling_available():
            http_get = ScraplingFetcher(stealthy=stealthy, **fetch_opts)
        else:
            from job_agent.sources.http import urllib_http

            http_get = lambda url: urllib_http(url)
    return CareerPageCrawler(http_get, robots=robots, rate_limiter=rate_limiter,
                             workday_post=workday_post)
