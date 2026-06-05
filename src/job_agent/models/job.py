"""Job posting model, normalised across all sources.

Extends the reference project's ``Job`` with the fields this product needs:
country/city, track, language requirements, a *soft* visa signal, and employment
type (so internships / traineeships / JPO on the international-org track are
first-class, not buried in free text).
"""

from enum import Enum

from pydantic import BaseModel, Field

from job_agent.models.candidate import Track


class VisaSignal(str, Enum):
    """What the posting *says* about sponsoring non-EU candidates.

    This is a SOFT factor for ranking — never a hard filter. A posting that says
    nothing (``unknown``) is still viable, especially for a candidate who holds a
    local degree and needs no sponsorship at all.
    """

    explicit_yes = "explicit_yes"  # "visa sponsorship available", "relocation support"
    likely = "likely"  # English-only team, international company — inferred
    unknown = "unknown"  # no signal either way (the default, and the common case)
    explicit_no = "explicit_no"  # "EU citizenship required", "must hold work permit"


class EmploymentType(str, Enum):
    full_time = "full_time"
    internship = "internship"
    traineeship = "traineeship"  # EU Blue Book / Schuman, corporate grad schemes
    jpo = "jpo"  # UN Junior Professional Officer (needs national sponsorship)
    other = "other"


class Job(BaseModel):
    source: str  # e.g. "eures", "arbeitsagentur", "welcometothejungle"
    external_id: str  # unique within source; DB dedupes on (source, external_id)
    title: str
    company: str
    country: str  # ISO-2
    city: str | None = None
    track: Track = Track.private
    source_type: str = "unknown"  # "pes" | "eures" | "niche" | "intl_org"
    languages_required: list[str] = Field(default_factory=list)  # ISO-639-1
    salary_eur: int | None = None  # annual gross if known
    description: str = ""
    url: str | None = None
    visa_signal: VisaSignal = VisaSignal.unknown
    employment_type: EmploymentType = EmploymentType.full_time
