# EU Job Agent

A job-search agent for **junior international graduates** (need-not-mandatory visa
support) who want to build a career in Europe — deliberately covering the
**small/medium employers and international organisations that do *not* recruit
through LinkedIn**.

Architecture patterns (dependency injection, multi-source Scout, observability,
offline-first testability) are adapted from the W-HS `job-agent-whs` reference
project; the domain model, source coverage, and the visa-feasibility engine are
new.

## Two tracks

- **Track A — private / SME**: legal route is national work authorisation
  (EU Blue Card, post-study job-seeker permits, **local-degree exemptions**).
  Visa sponsorship is a *soft* signal, never a hard filter.
- **Track B — international organisations**: UN / EU / NGO roles + internships /
  traineeships / JPO. Different legal status (often self-granted), very
  competitive at junior level.

## Visa feasibility, not a yes/no filter

The core insight: whether a candidate can take a job depends on
`(nationality, degree-country, field, salary) × job-country`. A non-EU graduate
**holding a local degree** is often exempt from employer sponsorship entirely
(e.g. CZ, PL: no work permit; DE/AT/CH: priority-check / facilitation). So jobs
that never mention "visa sponsorship" are still fully viable. See
`src/job_agent/visa/`.

> The encoded immigration rules are a starting point and must be verified against
> official sources before being shown to a user as advice.

## Current Status

Offline-first and live-capable. The test suite uses injected transports and makes no
network calls. Streamlit Live mode can use an OpenAI-compatible LLM, Jina embeddings,
Brave Search, Scrapling, EURES, public ATS feeds, and optional Supabase persistence.

## Discovery Strategy

The system does not require the user to know company names or recruitment domains.

1. An LLM creates multilingual search queries from the candidate's field, target
   country, cities, and local hiring terminology.
2. Brave Search finds public ATS pages, company-owned career portals, and job detail
   pages while excluding major aggregators.
3. Known ATS feeds are parsed structurally. Unknown career pages are fetched with
   Scrapling when installed, with a urllib fallback.
4. ATS fingerprints and direct job-detail extraction cover Workday, Ashby,
   SmartRecruiters, and company-specific portals such as `jobs.doosan.com`.

Country is the primary filter. City is displayed and used for location hints, but a
missing or unfamiliar city does not discard a country-matching vacancy. The search
diagnostics panel exposes query count, discovered companies, fetch success, source,
ATS, and employment-type distributions.

EURES uses its public POST search API and does not require a separate API key. It
covers 31 EEA/Swiss countries and returns public-employment-service vacancies.

## Main Components

- `Scout` — multilingual query planning, ATS discovery, web discovery, crawling,
  source isolation, deduplication, and observability.
- `Visa` — country-aware feasibility assessment; sponsorship remains a soft signal.
- `Matcher` — lexical fallback or optional semantic embeddings via Jina.
- `Writer` — grounded cover letters and tailored CV variants.
- `Tracker` — application lifecycle, reminders, and optional Supabase persistence.
- `Streamlit UI` — Demo/Live search, ranked matches, diagnostics, and tracking.

## Setup

```bash
uv sync --extra dev
uv run pytest
```

For the full local Live UI:

```bash
uv pip install -e ".[llm,ui,scrape]"
python -m playwright install chromium
streamlit run streamlit_app.py
```

Streamlit Cloud configuration is documented in
[`docs/STREAMLIT_SETUP.md`](docs/STREAMLIT_SETUP.md).
