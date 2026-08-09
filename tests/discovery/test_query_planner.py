from job_agent.discovery import DiscoveryQuery
from job_agent.discovery.query_planner import llm_query_planner


def test_llm_query_planner_returns_search_queries() -> None:
    planner = llm_query_planner(
        lambda prompt: '{"queries": ["site:jobs.doosan.com dobríš careers", '
                        '"Brno manufacturing kariera jobs"]}'
    )
    queries = planner(DiscoveryQuery(country="CZ", industry="international relations"), ["praha"])

    assert queries == ["site:jobs.doosan.com dobríš careers", "Brno manufacturing kariera jobs"]


def test_llm_query_planner_falls_back_on_invalid_output() -> None:
    planner = llm_query_planner(lambda prompt: "not json")
    queries = planner(DiscoveryQuery(country="CZ", keywords=["analyst"]), ["praha"])

    assert queries
    assert any("praha" in query for query in queries)
