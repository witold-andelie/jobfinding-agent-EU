"""Visa-feasibility engine.

Answers, for a given candidate and job: *can this person realistically take this
job, and does it require employer sponsorship?* Visa support is treated as
optional — the engine's whole point is that many routes (especially holding a
local degree) need no sponsorship at all.
"""

from job_agent.visa.engine import FeasibilityLevel, FeasibilityResult, assess
from job_agent.visa.rules import COUNTRY_RULES, CountryVisaRule
from job_agent.visa.signal import (
    PromptedVisaSignalLLM,
    SignalVerdict,
    VisaSignalClassifier,
    VisaSignalLLM,
    classify_keywords,
)

__all__ = [
    "COUNTRY_RULES",
    "CountryVisaRule",
    "FeasibilityLevel",
    "FeasibilityResult",
    "PromptedVisaSignalLLM",
    "SignalVerdict",
    "VisaSignalClassifier",
    "VisaSignalLLM",
    "assess",
    "classify_keywords",
]
