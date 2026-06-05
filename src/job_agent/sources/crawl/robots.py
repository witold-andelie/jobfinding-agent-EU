"""Real robots.txt compliance for the crawler.

The jobup.ch lesson, codified: before fetching a URL, consult the host's
robots.txt. ``RobotsTxtChecker`` fetches and caches robots.txt per host (via an
injected ``fetch`` seam, so it's offline-testable) and answers ``allowed(url)``
with the stdlib ``RobotFileParser``. A missing/unreadable robots.txt is treated as
allow-all (the web's convention).
"""

from __future__ import annotations

from typing import Callable
from urllib.parse import urlparse
from urllib.robotparser import RobotFileParser


class RobotsTxtChecker:
    def __init__(self, fetch: Callable[[str], str], user_agent: str = "*") -> None:
        self._fetch = fetch
        self._ua = user_agent
        self._cache: dict[str, RobotFileParser] = {}

    def _parser_for(self, url: str) -> RobotFileParser:
        parts = urlparse(url)
        origin = f"{parts.scheme}://{parts.netloc}"
        parser = self._cache.get(origin)
        if parser is None:
            parser = RobotFileParser()
            try:
                parser.parse(self._fetch(f"{origin}/robots.txt").splitlines())
            except Exception:  # noqa: BLE001 - no/broken robots.txt → allow (web convention)
                parser.parse([])
            self._cache[origin] = parser
        return parser

    def allowed(self, url: str) -> bool:
        return self._parser_for(url).can_fetch(self._ua, url)
