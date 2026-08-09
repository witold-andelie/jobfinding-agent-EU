"""LLM-assisted query planning for discovering unknown employer career sites."""

from __future__ import annotations

import json
import re
from collections.abc import Callable

from job_agent.discovery.base import DiscoveryQuery

QueryPlanner = Callable[[DiscoveryQuery, list[str]], list[str]]
Ask = Callable[[str], str]


def _fallback_queries(query: DiscoveryQuery, cities: list[str]) -> list[str]:
    role = " ".join(query.keywords) or query.industry or "professional"
    queries: list[str] = []
    for city in cities:
        queries.extend([
            f'"{city}" {role} (careers OR jobs OR hiring)',
            f'"{city}" {role} (práce OR kariera OR zaměstnání)',
            f'"{city}" {role} (vacancy OR stellen OR emploi OR praca)',
        ])
    return queries


fallback_queries = _fallback_queries


def llm_query_planner(ask: Ask) -> QueryPlanner:
    """Return a planner that asks the LLM for diverse, search-engine-safe queries."""

    def plan(query: DiscoveryQuery, cities: list[str]) -> list[str]:
        country = (query.country or "").upper()
        role = " ".join(query.keywords) or query.industry or "professional roles"
        prompt = f"""
You are a European job-discovery researcher. Create web-search queries that find
unknown employers' own career pages and public ATS job pages. Do not return URLs,
company names, or explanations. Return only JSON: {{"queries": ["..."]}}.

Target country: {country}
Target cities/regions: {", ".join(cities)}
Role or field: {role}

Requirements:
- Generate 6 to 12 diverse queries.
- Mix English and the target country's local language where useful.
- Include SMEs, manufacturing, logistics, engineering, services, and local employers,
  not only technology companies.
- Include terms such as careers, vacancies, jobs, kariera, práce, stellenangebote,
  recrutement, praca when appropriate.
- Exclude LinkedIn, Indeed, Glassdoor, job aggregators, and recruitment agencies.
""".strip()
        try:
            raw = ask(prompt)
            match = re.search(r"\{.*\}", raw, re.DOTALL)
            payload = json.loads(match.group(0) if match else raw)
            queries = [str(item).strip() for item in payload.get("queries", [])]
            queries = [item for item in queries if 5 <= len(item) <= 220]
            if queries:
                return queries[:12]
        except Exception:  # noqa: BLE001 - search falls back deterministically
            return _fallback_queries(query, cities)
        return _fallback_queries(query, cities)

    return plan
