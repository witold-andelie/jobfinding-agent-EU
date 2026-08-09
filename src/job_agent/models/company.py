"""Company target model — the 'company-first' half of source discovery.

The core coverage problem: SMEs (e.g. Bobcat in Czechia) often post only on their
own ATS, not on LinkedIn or even on aggregators. So we maintain a list of target
companies and, crucially, *which ATS each one uses* — then pull that ATS's
structured job feed directly. ``ats`` + ``ats_handle`` are what make a company
machine-fetchable.
"""

from enum import Enum

from pydantic import BaseModel


class ATSPlatform(str, Enum):
    """Applicant tracking systems with a known public job feed.

    DACH-heavy SMEs cluster on personio/softgarden/recruitee; international and
    tech companies on greenhouse/lever/ashby/workable; large corporates on
    workday/smartrecruiters (Bobcat's group uses Workday at jobs.doosan.com).
    """

    personio = "personio"
    greenhouse = "greenhouse"
    lever = "lever"
    smartrecruiters = "smartrecruiters"
    recruitee = "recruitee"
    softgarden = "softgarden"
    ashby = "ashby"
    workable = "workable"
    workday = "workday"
    unknown = "unknown"  # no ATS detected yet → falls back to Layer 3 page crawl


class CompanyTarget(BaseModel):
    """A company we want to monitor for openings.

    ``ats_handle`` is the tenant slug in the ATS URL, e.g. for
    ``https://acme.jobs.personio.de/`` the handle is ``"acme"``.
    """

    name: str
    country: str  # ISO-2
    ats: ATSPlatform = ATSPlatform.unknown
    ats_handle: str | None = None
    careers_url: str | None = None
    website: str | None = None
    city_hint: str | None = None  # search location used when a plain page has no job location
    industry: str | None = None
    is_sme: bool = True
    discovered_via: str = "seed"  # "registry" | "chamber" | "seed" | "ats_crawl"
