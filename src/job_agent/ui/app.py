"""EU Job Agent — Streamlit dashboard.

Run with:  streamlit run src/job_agent/ui/app.py
(install the UI extra first:  uv pip install -e '.[llm,ui]')

Ties the pipeline together: build a candidate profile (optionally parsed from a CV
via the configured LLM), see a visa-aware ranked shortlist, generate non-fabricated cover
letters, and track applications through their lifecycle. Degrades gracefully with
no LLM key — matching/tracking work offline; only CV-parse and cover-letter need it.
"""

from __future__ import annotations

import os

import streamlit as st

# On Streamlit Community Cloud, config comes from the dashboard "Secrets" (no .env in
# the repo). Mirror them into the environment so pydantic-settings (config.py) reads
# them. Locally this is a no-op (there is no secrets file; .env is used instead).
try:
    for _k, _v in st.secrets.items():
        os.environ.setdefault(_k, str(_v))
except Exception:  # noqa: BLE001 - no secrets configured → fine
    pass

from job_agent.config import get_settings  # noqa: E402
from job_agent.matching import shortlist  # noqa: E402
from job_agent.models.application import ApplicationStatus  # noqa: E402
from job_agent.models.candidate import CandidateProfile, Track  # noqa: E402
from job_agent.observability import InMemoryObservability, start_run  # noqa: E402
from job_agent.tracker import Tracker  # noqa: E402
from job_agent.tracker.state_machine import ALLOWED_TRANSITIONS  # noqa: E402
from job_agent.ui.demo_data import demo_jobs  # noqa: E402

st.set_page_config(page_title="EU Job Agent", layout="wide")
st.caption("build 2026-06-05-f")  # version heartbeat: if you see this, the latest code is live


def _application_store():
    """BISECT: Supabase construction disabled to isolate white-screen cause."""
    return None


def _job_store():
    """BISECT: Supabase construction disabled to isolate white-screen cause."""
    return None


# --- session state -----------------------------------------------------------
if "tracker" not in st.session_state:
    st.session_state.tracker = Tracker(_application_store())
if "obs" not in st.session_state:
    st.session_state.obs = InMemoryObservability()
if "letters" not in st.session_state:
    st.session_state.letters = {}  # job external_id -> cover letter text

tracker: Tracker = st.session_state.tracker
obs: InMemoryObservability = st.session_state.obs
settings = get_settings()
llm_enabled = bool(settings.llm_api_key)


def _llm_ask():
    from job_agent.agents.llm import LLMClient

    return LLMClient(obs=obs).ask


# --- sidebar: candidate profile ---------------------------------------------
st.sidebar.header("Candidate")
languages_raw = st.sidebar.text_input("Languages (ISO-639-1, comma)", value="en, fr")

if llm_enabled:
    pass
else:
    st.sidebar.info("Set LLM_API_KEY to enable CV parsing and cover letters.")

profile = CandidateProfile(
    nationality="CN",
    degree_country="CH",
    field="international relations",
    skills=[],
    languages=[lang.strip().lower() for lang in languages_raw.split(",") if lang.strip()],
    tracks=[Track.private],
)
st.sidebar.caption(f"LLM spend this session: ${obs.total_cost_usd():.4f}")


def _load_jobs():
    """Demo data, or a real multi-source Scout run for live mode."""
    if not source_mode.startswith("Live"):
        return demo_jobs(), [], {}
    from job_agent.agents import ScoutQuery
    from job_agent.discovery import DiscoveryQuery, keep_jobs_in_country
    from job_agent.discovery.query_planner import llm_query_planner
    from job_agent.discovery.seed_builder import load_seeds
    from job_agent.pipeline import brave_search_fn, build_live_scout, production_transports

    country = live_country.strip().upper() or None
    http_get, http_json, http_post = production_transports()
    scout = build_live_scout(
        http_get=http_get, http_json=http_json, http_post=http_post,
        seeds=load_seeds("seeds/seeds.json"),
        search_fn=brave_search_fn(settings),  # the discovery engine (if BRAVE_API_KEY set)
        search_cities=4,           # include Czech industrial hubs such as Dobříš
        search_max_companies=40,   # bound the fetch so the cloud app doesn't run out of memory
        obs=obs,
        web_query_planner=llm_query_planner(_llm_ask) if llm_enabled else None,
    )
    query = ScoutQuery(DiscoveryQuery(
        country=country,
        industry=profile.field,
        keywords=[k.strip() for k in live_keywords.split(",") if k.strip()],
    ))
    try:
        result = scout.run(query)
        jobs = result.jobs
        # Sources/discovered tenants are cross-border → keep only target-country jobs.
        if country:
            jobs = keep_jobs_in_country(jobs, country)
        errors = list(result.errors)
        diagnostics = dict(result.diagnostics)
        diagnostics["jobs_after_country_filter"] = len(jobs)
        diagnostics["filtered_out_by_country"] = len(result.jobs) - len(jobs)
        # Persist the relevant (in-country) jobs to Supabase if configured.
        store = _job_store()
        if store is not None and jobs:
            try:
                store.upsert_jobs(jobs)
            except Exception as exc:  # noqa: BLE001
                errors.append(f"persist failed: {exc}")
        return jobs, errors, diagnostics
    except Exception as exc:  # noqa: BLE001 - surface, don't crash the UI
        return [], [f"live scout failed: {exc}"], {}


# --- main --------------------------------------------------------------------
st.title("EU Job Agent")
st.write(f"profile languages = {profile.languages}")
