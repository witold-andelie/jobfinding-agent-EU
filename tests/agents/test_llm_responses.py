from job_agent.agents.llm import LLMClient
from job_agent.config import Settings


class _Usage:
    input_tokens = 12
    output_tokens = 4


class _Response:
    output_text = "response result"
    usage = _Usage()


class _FakeClient:
    class responses:
        @staticmethod
        def create(**kwargs):  # type: ignore[no-untyped-def]
            assert kwargs["model"] == "gpt-5.6-luna"
            return _Response()


def test_responses_api_mode_uses_responses_client() -> None:
    client = LLMClient(
        settings=Settings(
            llm_api_key="test",
            llm_base_url="https://opencode.ai/zen/go/v1/responses",
            llm_model="gpt-5.6-luna",
            llm_api_mode="responses",
        ),
        client=_FakeClient(),
    )
    assert client.ask("hello") == "response result"
