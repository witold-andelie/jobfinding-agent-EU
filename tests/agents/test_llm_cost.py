"""LLMClient records an llm_event (tokens + cost) against the active run — offline."""

from job_agent.agents.llm import LLMClient, _estimate_cost
from job_agent.observability import InMemoryObservability, start_run


class _Usage:
    prompt_tokens = 120
    completion_tokens = 30


class _Msg:
    content = '{"signal": "likely", "rationale": "ok"}'


class _Choice:
    message = _Msg()


class _Resp:
    choices = [_Choice()]
    usage = _Usage()


class _FakeClient:
    class chat:  # noqa: N801
        class completions:  # noqa: N801
            @staticmethod
            def create(**kwargs):  # type: ignore[no-untyped-def]
                return _Resp()


def test_cost_estimate_is_none_without_usage() -> None:
    assert _estimate_cost(None, None) is None
    assert _estimate_cost(1000, 1000) is not None and _estimate_cost(1000, 1000) > 0


def test_ask_records_event_with_tokens_and_cost() -> None:
    obs = InMemoryObservability()
    client = LLMClient(client=_FakeClient(), obs=obs)

    ctx = start_run("test")
    out = client.ask("classify this posting")

    assert out.startswith("{")
    assert len(obs.llm_events) == 1
    event = obs.llm_events[0]
    assert event["run_id"] == ctx.run_id  # attributed to the active run
    assert event["prompt_tokens"] == 120 and event["completion_tokens"] == 30
    assert event["cost_usd"] > 0
    assert obs.total_cost_usd() == event["cost_usd"]


def test_ask_without_obs_does_not_record() -> None:
    client = LLMClient(client=_FakeClient())  # no obs
    assert client.ask("x").startswith("{")  # works, just no event recorded
