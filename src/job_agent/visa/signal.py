"""Visa-sponsorship signal classification — hybrid keyword + LLM.

Pipeline (cheap → expensive):
1. ``classify_keywords`` — pure, multilingual, negation-aware. Settles the clear
   cases (strong positive / negative phrases) for free, offline, deterministically.
2. Only the ambiguous middle (``unknown`` / conflicting) is escalated to an LLM,
   behind a DI seam that is off by default — so tests and offline runs never call
   out. Results are cached by text hash to avoid paying twice for the same posting.

The output ``visa_signal`` is a SOFT factor for ranking, never a hard filter
(see ``job_agent.visa.engine``).
"""

from __future__ import annotations

import hashlib
import json
import re
from dataclasses import dataclass
from typing import Protocol

from job_agent.models.job import Job, VisaSignal

# --- keyword lexicons (lowercased; DE/FR/EN cover our target markets) ---------

_POSITIVE = (
    "visa sponsorship", "we sponsor", "sponsorship available", "will sponsor",
    "happy to sponsor", "relocation package", "relocation support",
    "relocation assistance", "we welcome international", "open to international",
    "visa-beschaffung", "unterstützung bei der visa", "umzugsunterstützung",
    "parrainage de visa", "aide à la relocalisation",
)
_NEGATIVE = (
    "unable to sponsor", "not able to sponsor", "cannot sponsor", "do not sponsor",
    "no visa sponsorship", "no sponsorship", "without sponsorship",
    "must already have the right to work", "right to work in", "work permit required",
    "valid work permit", "eu citizenship required", "eu/eea citizenship",
    "must hold a work permit", "existing work authorization",
    "keine visa", "kein visum", "arbeitserlaubnis erforderlich", "eu-staatsbürgerschaft",
    "permis de travail requis", "citoyenneté de l'ue",
)
_LIKELY = (
    "english-speaking team", "english is our company language", "no german required",
    "international team", "relocation",
)
_NEGATORS = ("not ", "no ", "non-", "unable", "cannot", "can't", "won't", "without",
             "kein", "keine", "nicht", "ne ", "pas ", "sans ")


@dataclass(frozen=True)
class SignalVerdict:
    signal: VisaSignal
    rationale: str
    source: str  # "keyword" | "llm" | "none"


def _negated(text: str, phrase_idx: int) -> bool:
    """Whether a negator appears just before a matched positive phrase."""
    window = text[max(0, phrase_idx - 28):phrase_idx]
    return any(neg in window for neg in _NEGATORS)


def classify_keywords(text: str) -> SignalVerdict:
    """Deterministic, offline first pass. Returns ``unknown`` when no phrase matches."""
    low = text.lower()

    for phrase in _NEGATIVE:
        if phrase in low:
            return SignalVerdict(VisaSignal.explicit_no, f"matched '{phrase}'", "keyword")

    for phrase in _POSITIVE:
        idx = low.find(phrase)
        if idx != -1:
            if _negated(low, idx):
                return SignalVerdict(
                    VisaSignal.explicit_no, f"negated '{phrase}'", "keyword"
                )
            return SignalVerdict(VisaSignal.explicit_yes, f"matched '{phrase}'", "keyword")

    for phrase in _LIKELY:
        if phrase in low:
            return SignalVerdict(VisaSignal.likely, f"matched '{phrase}'", "keyword")

    return SignalVerdict(VisaSignal.unknown, "no keyword signal", "keyword")


# --- LLM seam (off by default) ------------------------------------------------


class VisaSignalLLM(Protocol):
    def classify(self, text: str) -> SignalVerdict: ...


_PROMPT = (
    "You decide whether a job posting will sponsor a NON-EU candidate who needs a "
    "work visa. Be conservative and account for negation; the text may be in German, "
    "French, Czech, or Polish.\n"
    "Use exactly these labels:\n"
    "- explicit_yes: ONLY when sponsorship, relocation, or handling work-permit "
    "paperwork is CONCRETELY stated. Do not infer it from a friendly or "
    "'international' tone.\n"
    "- likely: international / English-speaking / welcomes-diverse-backgrounds, but "
    "sponsorship is not concretely promised.\n"
    "- explicit_no: EU citizenship or an existing work permit is required, or "
    "sponsorship is explicitly refused.\n"
    "- unknown: nothing indicates either way.\n"
    'Reply with ONLY JSON: {{"signal": "<one label>", "rationale": "<short>"}}.'
    "\n\nPosting:\n{text}"
)


class PromptedVisaSignalLLM:
    """Wraps a generic ``ask(prompt) -> str`` LLM call (the BaseAgent seam).

    Pure w.r.t. I/O: the network lives entirely in the injected ``ask`` callable,
    so tests pass a fake ``ask`` and exercise the full LLM branch offline.
    """

    def __init__(self, ask) -> None:  # ask: Callable[[str], str]
        self._ask = ask

    def classify(self, text: str) -> SignalVerdict:
        raw = self._ask(_PROMPT.format(text=text[:4000]))
        match = re.search(r"\{.*\}", raw, re.DOTALL)
        if not match:
            return SignalVerdict(VisaSignal.unknown, "unparseable LLM reply", "llm")
        try:
            data = json.loads(match.group(0))
            signal = VisaSignal(data.get("signal", "unknown"))
        except (json.JSONDecodeError, ValueError):
            return SignalVerdict(VisaSignal.unknown, "invalid LLM JSON", "llm")
        return SignalVerdict(signal, str(data.get("rationale", "")), "llm")


# --- hybrid classifier --------------------------------------------------------


class VisaSignalClassifier:
    """Keyword first; escalate only the ambiguous middle to the LLM; cache results."""

    def __init__(
        self,
        llm: VisaSignalLLM | None = None,
        cache: dict[str, SignalVerdict] | None = None,
    ) -> None:
        self._llm = llm
        self._cache = cache if cache is not None else {}

    def classify(self, text: str) -> SignalVerdict:
        verdict = classify_keywords(text)
        # Confident keyword hit, or no LLM available → done (offline-safe).
        if verdict.signal is not VisaSignal.unknown or self._llm is None:
            return verdict
        key = hashlib.sha256(text.encode("utf-8")).hexdigest()
        if key in self._cache:
            return self._cache[key]
        result = self._llm.classify(text)
        self._cache[key] = result
        return result

    def enrich(self, job: Job) -> Job:
        """Return a copy of ``job`` with ``visa_signal`` populated."""
        text = f"{job.title}\n{job.description}".strip()
        return job.model_copy(update={"visa_signal": self.classify(text).signal})

    def enrich_jobs(self, jobs: list[Job]) -> list[Job]:
        return [self.enrich(j) for j in jobs]
