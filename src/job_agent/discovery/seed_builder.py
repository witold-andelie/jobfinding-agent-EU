"""Build a *verified* ATS seed library from known career-page URLs.

The high-quality counterpart to brute force: instead of guessing companies from a
registry, you feed in career-page URLs you already trust (curated lists, partner
companies, alumni employers), fingerprint each one's ATS, and get back
``CompanyTarget`` seeds that can be fetched as structured feeds. No Brave quota, no
ToS-grey scraping. ``verify_seed`` confirms a handle actually returns jobs, so the
library never accumulates dead entries.
"""

from __future__ import annotations

import json
import re
from dataclasses import dataclass
from pathlib import Path

from job_agent.discovery.fingerprint import detect_ats
from job_agent.models.company import ATSPlatform, CompanyTarget
from job_agent.sources import HttpGet, fetch_company_jobs
from job_agent.sources.ats import ADAPTERS

# Legal-form suffixes to strip when slugifying a company name into an ATS handle.
_LEGAL_SUFFIX = re.compile(
    r"\b(s\.?r\.?o\.?|a\.?s\.?|spol|gmbh|ag|sa|sarl|ltd|limited|kft|inc|llc|se)\b\.?",
    re.I,
)


@dataclass
class SeedEntry:
    name: str
    country: str  # ISO-2
    careers_url: str
    industry: str | None = None


@dataclass
class HandleCandidate:
    handle: str
    name: str | None = None
    country: str = ""
    industry: str | None = None


def build_seeds(entries: list[SeedEntry], http_get: HttpGet) -> tuple[list[CompanyTarget], list[str]]:
    """Fingerprint each entry's careers page → verified seeds + a list of failures."""
    seeds: list[CompanyTarget] = []
    failed: list[str] = []
    for entry in entries:
        try:
            page = http_get(entry.careers_url)
        except Exception:  # noqa: BLE001 - one unreachable page must not abort the batch
            failed.append(entry.name)
            continue
        platform, handle = detect_ats(page or entry.careers_url)
        if platform is ATSPlatform.unknown or not handle:
            failed.append(entry.name)
            continue
        seeds.append(
            CompanyTarget(
                name=entry.name,
                country=entry.country,
                industry=entry.industry,
                ats=platform,
                ats_handle=handle,
                careers_url=entry.careers_url,
                discovered_via="curated",
            )
        )
    return seeds, failed


def verify_seed(company: CompanyTarget, http_get: HttpGet) -> int:
    """Return how many jobs the seed's ATS feed yields (0 ⇒ dead/empty handle)."""
    try:
        return len(fetch_company_jobs(company, http_get))
    except Exception:  # noqa: BLE001 - a broken feed counts as zero, not a crash
        return 0


def handle_candidates(
    names: list[str], country: str, industry: str | None = None
) -> list[HandleCandidate]:
    """Derive ATS-handle guesses from company names (semi-automatic collection input).

    For each name we emit a couple of slug variants (compact + hyphenated). The
    prober verifies them, so wrong guesses simply fail — keep the name list curated
    rather than brute-enumerated to stay polite.
    """
    candidates: list[HandleCandidate] = []
    seen: set[str] = set()
    for name in names:
        core = _LEGAL_SUFFIX.sub("", name).strip()
        words = re.findall(r"[a-z0-9]+", core.lower())
        if not words:
            continue
        for handle in {"".join(words), "-".join(words)}:
            if handle and handle not in seen:
                seen.add(handle)
                candidates.append(HandleCandidate(handle, name, country, industry))
    return candidates


def probe_ats_handles(
    candidates: list[HandleCandidate],
    http_get: HttpGet,
    *,
    platforms: list[ATSPlatform] | None = None,
    min_jobs: int = 1,
) -> list[CompanyTarget]:
    """Probe each candidate handle against public ATS feeds; keep the live ones.

    Hits only the ATS providers' public job feeds (no Brave, no ToS-grey scraping),
    parses the response, and keeps a seed only when the feed yields ≥ ``min_jobs``
    real jobs. The first platform that resolves for a handle wins.
    """
    platforms = platforms or list(ADAPTERS.keys())
    seeds: list[CompanyTarget] = []
    for cand in candidates:
        for platform in platforms:
            adapter = ADAPTERS.get(platform)
            if adapter is None:
                continue
            company = CompanyTarget(
                name=cand.name or cand.handle,
                country=cand.country,
                industry=cand.industry,
                ats=platform,
                ats_handle=cand.handle,
                discovered_via="ats_probe",
            )
            try:
                jobs = adapter.parse(http_get(adapter.feed_url(cand.handle)), company)
            except Exception:  # noqa: BLE001 - dead handle / 404 → try next platform
                continue
            if len(jobs) >= min_jobs:
                seeds.append(company)
                break
    return seeds


def save_seeds(seeds: list[CompanyTarget], path: str | Path) -> None:
    """Persist verified seeds to JSON so the library accumulates across runs."""
    data = [s.model_dump(mode="json") for s in seeds]
    Path(path).write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")


def load_seeds(path: str | Path) -> list[CompanyTarget]:
    """Load a persisted seed library (returns [] if the file does not exist)."""
    p = Path(path)
    if not p.exists():
        return []
    return [CompanyTarget(**d) for d in json.loads(p.read_text(encoding="utf-8"))]
