"""Hybrid visa-signal classifier: keyword layer + LLM escalation + caching."""

from job_agent.agents.llm import LLMClient
from job_agent.models.job import Job, VisaSignal
from job_agent.visa import (
    PromptedVisaSignalLLM,
    VisaSignalClassifier,
    classify_keywords,
)

# --- keyword layer (pure, offline) -------------------------------------------


def test_keyword_explicit_yes() -> None:
    assert classify_keywords("Visa sponsorship available.").signal is VisaSignal.explicit_yes


def test_keyword_german_positive() -> None:
    v = classify_keywords("Wir bieten Unterstützung bei der Visa-Beschaffung.")
    assert v.signal is VisaSignal.explicit_yes


def test_keyword_negation_flips_to_no() -> None:
    v = classify_keywords("We are unfortunately not able to sponsor work visas.")
    assert v.signal is VisaSignal.explicit_no


def test_keyword_explicit_no_phrase() -> None:
    assert classify_keywords("EU citizenship required.").signal is VisaSignal.explicit_no


def test_keyword_likely_and_unknown() -> None:
    assert classify_keywords("We are an English-speaking team.").signal is VisaSignal.likely
    assert classify_keywords("Join our growing analytics group.").signal is VisaSignal.unknown


# --- hybrid: escalation only for the ambiguous middle ------------------------


class _SpyLLM:
    def __init__(self, signal: VisaSignal) -> None:
        self.signal = signal
        self.calls = 0

    def classify(self, text: str):  # type: ignore[no-untyped-def]
        from job_agent.visa import SignalVerdict

        self.calls += 1
        return SignalVerdict(self.signal, "llm-judged", "llm")


def test_confident_keyword_does_not_call_llm() -> None:
    spy = _SpyLLM(VisaSignal.likely)
    clf = VisaSignalClassifier(llm=spy)
    assert clf.classify("Visa sponsorship available.").signal is VisaSignal.explicit_yes
    assert spy.calls == 0  # keyword settled it


def test_ambiguous_escalates_and_caches() -> None:
    spy = _SpyLLM(VisaSignal.likely)
    clf = VisaSignalClassifier(llm=spy)
    text = "Join our growing analytics group in Prague."  # no keyword signal
    assert clf.classify(text).signal is VisaSignal.likely
    assert clf.classify(text).signal is VisaSignal.likely  # repeated
    assert spy.calls == 1  # cached: LLM hit only once


def test_offline_no_llm_stays_unknown() -> None:
    clf = VisaSignalClassifier(llm=None)
    assert clf.classify("ambiguous text").signal is VisaSignal.unknown


def test_enrich_sets_visa_signal_on_job() -> None:
    job = Job(source="s", external_id="1", title="Engineer",
              company="C", country="DE", description="Relocation package provided.")
    enriched = VisaSignalClassifier().enrich(job)
    assert enriched.visa_signal is VisaSignal.explicit_yes


# --- LLM seam (DeepSeek) parsing + DI, all offline ---------------------------


def test_prompted_llm_parses_json_reply() -> None:
    llm = PromptedVisaSignalLLM(ask=lambda prompt: 'Sure: {"signal": "explicit_no", "rationale": "EU only"}')
    v = llm.classify("some posting")
    assert v.signal is VisaSignal.explicit_no
    assert v.source == "llm"


def test_prompted_llm_handles_garbage() -> None:
    llm = PromptedVisaSignalLLM(ask=lambda prompt: "I cannot help with that")
    assert llm.classify("x").signal is VisaSignal.unknown


def test_prompt_is_conservative_about_explicit_yes() -> None:
    # Capture the prompt the LLM is given; it must instruct concrete-only explicit_yes.
    seen: dict[str, str] = {}

    def _ask(prompt: str) -> str:
        seen["p"] = prompt
        return '{"signal": "likely", "rationale": "x"}'

    PromptedVisaSignalLLM(ask=_ask).classify("an international, friendly team")
    assert "CONCRETELY" in seen["p"] and "Do not infer" in seen["p"]


def test_llm_client_uses_injected_client_offline() -> None:
    # Fake OpenAI-shaped client → no network, no openai dependency, no credentials.
    class _Msg:
        content = '{"signal": "likely", "rationale": "english team"}'

    class _Choice:
        message = _Msg()

    class _Resp:
        choices = [_Choice()]

    class _FakeOpenAI:
        class chat:  # noqa: N801
            class completions:  # noqa: N801
                @staticmethod
                def create(**kwargs):  # type: ignore[no-untyped-def]
                    return _Resp()

    client = LLMClient(client=_FakeOpenAI())
    llm = PromptedVisaSignalLLM(ask=client.ask)
    assert llm.classify("english-speaking startup").signal is VisaSignal.likely
