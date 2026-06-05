"""Layer 3 — career-page crawling (last resort for companies with no ATS feed).

Politeness is built in via injectable seams: a ``RobotsChecker`` (respect
robots.txt) and a ``RateLimiter`` (throttle requests). Defaults are permissive/no-op
so tests run offline and instantly; production wires real implementations. Always
check each site's Terms of Service before crawling (the reference project excluded
StepStone for exactly this reason).
"""

from job_agent.sources.crawl.career_page import (
    AllowAllRobots,
    CareerPageCrawler,
    NoOpRateLimiter,
    extract_jobs,
    find_careers_url,
)
from job_agent.sources.crawl.robots import RobotsTxtChecker
from job_agent.sources.crawl.scrapling_fetcher import (
    ScraplingFetcher,
    build_career_crawler,
    scrapling_available,
)

__all__ = [
    "AllowAllRobots",
    "CareerPageCrawler",
    "NoOpRateLimiter",
    "RobotsTxtChecker",
    "ScraplingFetcher",
    "build_career_crawler",
    "extract_jobs",
    "find_careers_url",
    "scrapling_available",
]
