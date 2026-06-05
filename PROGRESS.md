# Progress Log

## Sprint 0 — Framework & Scout orchestrator
Status: **complete** (offline, 24 tests passing, 0 live calls).

Locked the architecture and stood up the spine of the agent, borrowing proven
patterns from the `job-agent-whs` reference (DI seams, `run_context`, observability
wrapper, dispatch-table resilience, `(source, external_id)` dedupe, credential
guards) while replacing its domain with this product's.

**Built:**
- **Models** — `Job` (country/track/visa_signal/employment_type), `CandidateProfile`
  (nationality × degree_country), `CompanyTarget` (+ `ATSPlatform`).
- **Visa feasibility engine** (`visa/`) — sponsorship is a *soft* signal; local-degree
  exemptions encoded for 11 countries; Track-B international-org route bypasses permits.
- **Discovery layer** (`discovery/`) — `SeedDiscoverer`, `AtsDetectDiscoverer`
  (ATS fingerprinting for broad search), `RegistryDiscoverer` (registry endpoints,
  ingestion stub).
- **Sources** — Layer 2 ATS adapters (Personio, Greenhouse) + Track-B intl-org
  (ReliefWeb). Injected `HttpGet` seam ⇒ everything testable offline.
- **Infra** — `config` (provider-agnostic LLM + Supabase, fail-fast guards),
  `observability` (RunContext + in-memory store), `persistence` (JobStore + in-memory,
  dedupe).
- **ScoutAgent** — orchestrates Track A (discover → ATS fetch) + Track B, with
  per-source failure isolation, observability, and dedupe+persist.

Two end-to-end demos pass: Czech IT SME (local-degree, no sponsorship) and Geneva
IR graduate (Swiss-degree private market + Geneva international orgs).

## Sprint 1 — Real Layer-1 sources + hybrid visa-signal classifier
Status: **complete** (offline, 39 tests passing).

- **Hybrid `visa_signal` classifier** (`visa/signal.py`): multilingual, negation-aware
  keyword layer (free, deterministic) → escalates only the ambiguous middle to an LLM
  behind a DI seam (off by default) → caches by text hash.
- **LLM = DeepSeek** (`agents/llm.py`): OpenAI-compatible API via the `openai` SDK
  (lazy import, DI seam, credential guard). `LLMClient().ask` feeds `PromptedVisaSignalLLM`.
- **`BoardSource` abstraction** (`sources/board.py` + `sources/http.py`): richer
  `HttpJson` transport (supports auth headers) + stdlib production `urllib_http`.
- **Aggregators** (`sources/aggregators/`): Arbeitsagentur (DE, adapted from reference),
  EURES (EU/EEA breadth — needs partner creds), Job-Room (CH official PES, since
  Switzerland is outside EURES). ReliefWeb is now a `BoardSource` too.
- **Scout refactor**: drives `discoverers` (Track A companies → ATS) + `board_sources`
  (aggregators + Track B) uniformly, each with per-source failure isolation.
  > External API response shapes (EURES, Job-Room) are defensive and need verifying
  > against the live APIs before real fetches; offline fixtures lock the mappings.

## Sprint 1.5 — Value loop closed
Status: **complete** (offline, 44 tests passing).

- Wired `VisaSignalClassifier` into Scout: jobs are auto-tagged with `visa_signal`
  (keyword layer free; LLM off by default) right after dedupe.
- `matching/shortlist.py`: `shortlist(candidate, jobs)` ranks by visa feasibility
  (dominant) + signal + language fit; filters `red` by default.
- End-to-end pipeline test + live demo: `ScoutAgent.run()` → enrich → `shortlist()`
  produces a ranked, visa-aware list (verified on the Geneva IR persona).

## Sprint 2 — Matcher (relevance) + cost observability
Status: **complete** (offline 55 tests; verified live on DeepSeek).

- **A — quality + cost**: tightened the visa-signal prompt so `explicit_yes` needs a
  concrete statement (killed the over-read); `LLMClient` now records an `llm_event`
  (tokens + estimated USD cost + duration) per call against the active run
  (`InMemoryObservability.total_cost_usd()`).
- **B — Matcher**: DeepSeek has **no embeddings endpoint** (verified 404), so relevance
  defaults to offline **lexical** similarity, with a pluggable `Embedder` seam
  (`SemanticSimilarity`) for a third-party provider. `shortlist` now ranks
  lexicographically: feasibility tier first, then content score (relevance + signal +
  language). `analyze_gap` does per-job DeepSeek gap analysis (matched/missing/emphasis).
  `CandidateProfile` gained `skills`.

Known limitation: lexical similarity misses semantic relatedness (e.g. a global-health
UN role scored 0 against an IR candidate). Plugging an embedder via the seam fixes it.

## Sprint 3 — CV parsing + Writer (full loop closed)
Status: **complete** (offline 65 tests; verified live end-to-end on DeepSeek).

- **CV parsing** (`parsing/cv.py`): DeepSeek extracts a `ParsedCV` (field/skills/
  languages/years/degree_country) from raw CV text; nationality is kept separate
  (not reliably on a CV, yet the key visa input) and merged via `to_profile`.
- **Writer** (`writing/cover_letter.py`): `generate_cover_letter` — grounded strictly
  in the real profile, no fabrication; weaves in gap-analysis emphasis; configurable
  language. `unsupported_claims` flags any "experience with X" not backed by the profile.
- **Fixed** a lexical-similarity bug found via live demo: multi-word skills
  ("policy analysis") are now tokenised so they match word-tokenised job text
  (PA role 0.0 → 0.35 for the IR candidate).

Live capstone: CV → parse → shortlist → gap → cover letter runs in 3 DeepSeek calls
for ~$0.0006 total, producing a tailored, non-fabricated letter (anti-fabrication
check clean).

## Sprint 4 — Persistence (Supabase backbone)
Status: **complete** (offline 69 tests; mock-tested, no live DB calls).

- `db/client.py`: `SupabaseClient` DI wrapper (lazy `supabase` import — import-safe
  offline), adapted from the reference.
- `db/migrations/001_init.sql`: schema for `jobs` (our extended model + `unique(source,
  external_id)` dedupe), `applications` (for Tracker), `agent_runs`, `llm_events`.
  pgvector deferred until an embedder lands.
- `persistence/supabase.py` `SupabaseJobStore` + `observability/supabase.py`
  `SupabaseObservability`: implement the existing protocols → **drop-in** for the
  in-memory stores; Scout/LLMClient unchanged. Verified Scout works end-to-end against
  a fake Supabase client.

To go live: put SUPABASE_URL/KEY in `.env`, apply `001_init.sql`, swap
`InMemoryJobStore`→`SupabaseJobStore(SupabaseClient())`.

## Sprint 5 — Brute-force search (registry → crawl), step 1: CZ + CH
Status: **registry layer complete** (offline 80 tests; ARES verified LIVE).

- `discovery/registry.py`: `AresClient` (CZ, free, **verified live** — returns real
  companies), `ZefixClient` (CH, needs a Zefix API account / Basic auth),
  `RegistryDiscoverer` routes by country → `CompanyTarget`. Built to probed API shapes.
- `sources/crawl/career_page.py`: Layer-3 crawler — `find_careers_url` + `extract_jobs`
  + ATS hand-off (uses the structured adapter when a known ATS is detected) + `robots`
  / `rate_limiter` politeness seams.
- `discovery/brute_force.py`: `brute_force_search` pipeline (registry → `DomainResolver`
  → crawl), per-company isolation. `docs/legal.md` captures ToS/robots/GDPR posture.

- `discovery/resolve.py`: `SearchDomainResolver` (Brave Search) resolves company→website
  with a **name↔domain guard**, aggregator **blocklist**, **negative caching**, a
  persistent **`FileCache`** (never re-spend on a company), and a per-session
  **`max_calls` budget guard** — the Brave key is **1000 req/month**. Verified live once.

Honest findings from the live CZ run (brute-force is a noisy wide net):
- ARES name-search returns shell/foreign entities, not hiring SMEs (no real NACE filter).
- Web resolution picks aggregators / same-named firms → name-guard + blocklist help,
  but yield stays low. Real SME sites are often JS-rendered or 403 → static crawl misses.
=> Brute-force is **supplementary**; the seed-list + ATS path is far higher quality.

## Sprint 6 — Deepen the high-quality path (chose quality over brute force)
Status: **complete** (offline 91 tests).

- **jobup.ch / jobs.ch excluded**: their JSON API is under `/api/`, which
  `robots.txt` Disallows — same call as StepStone. Recorded in `docs/legal.md`.
  Swiss coverage stays on the official Job-Room source + ATS feeds.
- **`RobotsTxtChecker`** (`sources/crawl/robots.py`): real robots.txt enforcement via
  stdlib `RobotFileParser` (fetch seam, cached per host) — the jobup lesson codified.
  Tested against jobup.ch's actual robots.txt.
- **`seed_builder.py`**: `build_seeds(entries, http)` fingerprints known career-page
  URLs → **verified** ATS `CompanyTarget` seeds; `verify_seed` confirms a handle returns
  jobs. **Semi-automatic collection**: `handle_candidates(names, country)` derives
  ATS-handle guesses from company names → `probe_ats_handles` hits the public ATS feeds
  and keeps only the live ones → `save_seeds`/`load_seeds` persist the library.
  **Verified live**: 6 names → 4 real Greenhouse boards (gitlab 161, figma 159, brex 227,
  monzo 59 live jobs). Zero Brave, ToS-clean (public feeds).

Hit rate depends on having the right ATS adapters: we ship Personio + Greenhouse;
DACH SMEs also use **softgarden / Recruitee / Lever** — adding those adapters would
raise CZ/CH yield.

## Sprint 7 — More ATS adapters (broaden probe coverage)
Status: **complete** (offline 97 tests; Lever verified live).

- **Lever** (`api.lever.co/v0/postings/{handle}?mode=json`) + **Recruitee**
  (`{handle}.recruitee.com/api/offers/`) adapters, built to the **probed live shapes**,
  registered in `ADAPTERS`. Prober now spans 4 platforms (Personio, Greenhouse, Lever,
  Recruitee). Live check: `ledger`→lever (1 job), `gitlab`→greenhouse (161).
- **softgarden NOT added** — its public feed isn't a clean `{handle}` API (per-tenant
  frontend tokens), so it doesn't fit the probe model. Needs a sample tenant URL.
- **Workday added** (`sources/ats/workday.py`, `fetch_workday_jobs`): large corporates
  (e.g. Doosan Bobcat at jobs.doosan.com). CXS **POST** API, verified live on NVIDIA
  (parsed real jobs). Handle is `tenant|dc|site` → **not auto-probable** (must be
  configured per company); lives outside the GET `ADAPTERS` registry.

## Sprint 8 — Tracker + Streamlit UI (product loop complete)
Status: **complete** (offline 110 tests; UI boots via AppTest).

- **Tracker** (`tracker/`, 4th agent): `Application` model + status state machine
  (new→applied→interview→offer→accepted/rejected/withdrawn) with validated transitions
  (`InvalidTransition`), `applied_at` stamping, and **follow-up reminders**
  (`due_followups(days=N)`). `ApplicationStore` seam + in-memory store. Pure, tested.
- **Streamlit UI** (`ui/app.py`): sidebar profile (or paste-CV→DeepSeek parse), a
  visa-aware ranked **Matches** tab (cover-letter + track buttons) and an
  **Applications** tab driving the Tracker. Degrades gracefully with no LLM key.
  Verified with `streamlit.testing.v1.AppTest` (boots, renders, tracking works).
- Run: `uv pip install -e '.[llm,ui]'` then `streamlit run src/job_agent/ui/app.py`.

All four agents now exist: Scout · Matcher(shortlist) · Writer · Tracker, + UI.

## Sprint 9 — Demo → usable (persistence + live sources in the UI)
Status: **complete** (offline 112 tests; UI AppTest green).

- **`SupabaseApplicationStore`** (`persistence/supabase.py`): drop-in for the in-memory
  application store; `applications` schema reworked to a UUID `id` + denormalised columns
  matching the `Application` model (incl. `history` jsonb). Round-trip verified through a
  stateful fake Supabase table + the Tracker.
- **`pipeline.py`** `build_live_scout(...)`: assembles ATS seeds + Arbeitsagentur/EURES/
  Job-Room + ReliefWeb into one ScoutAgent; `production_transports()` = stdlib urllib
  transports. Tested offline via injected fakes.
- **UI live mode**: sidebar "Demo / Live" toggle + country/keywords; live runs
  `build_live_scout` (loads `seeds/seeds.json` if present), shows per-source errors.
  Applications persist to Supabase when `SUPABASE_URL/KEY` set, else in-memory.

## Sprint 10 — Semantic matching (embeddings)
Status: **complete** (offline 117 tests; Jina verified live).

- **`matching/embedders.py`**: `OpenAICompatibleEmbedder` (one impl serves OpenAI /
  Jina / Voyage / local ollama via `embedding_base_url`), `build_embedder(settings)`
  factory, `default_similarity()` → semantic when configured, offline lexical otherwise.
  Wired into the UI's shortlist. Config keys added (`EMBEDDING_*`).
- **Provider = Jina** (`jina-embeddings-v3`, multilingual). Live result: the IR
  candidate's WHO global-health role scored **0.65 semantic vs 0.00 lexical** and now
  correctly outranks a backend-dev role (0.48) — fixes the lexical blind spot.
- **Resilience**: `SemanticSimilarity` returns 0.0 on embed failure (ranking never
  crashes). **Hermetic tests**: `tests/conftest.py` blanks credential env vars so the
  suite never makes live API calls (it was spending Jina quota via the UI AppTest).

## Sprint 11 — Tailored CV variant (.docx) — application package complete
Status: **complete** (offline 120 tests; verified live).

- CV parser now also extracts `name`/`contact`/`experience`/`education` (verbatim).
- **`writing/cv_variant.py`**: `rank_skills` (deterministic re-ordering — gap matches +
  job-overlap first, nothing invented/dropped), `tailored_summary` (DeepSeek, grounded),
  `build_cv_docx` / `generate_cv_variant` (python-docx, `docx` extra). Experience &
  education carried over verbatim — no fabrication.
- **UI**: a "📄 CV variant (.docx)" button (when a CV was parsed) → download the tailored
  CV. Live demo: skills re-ranked policy-first, grounded summary, real experience kept.
- Application package = tailored cover letter + tailored CV, both non-fabricated.

## Sprint 12 — Job-Room real API (the live CH source)
Status: **complete** (offline 121 tests; verified live — 30 real Swiss jobs).

- **Job-Room rewritten to the real API** (probed live): **POST** `_search?page=&size=`
  with body `{}` → array of `jobAdvertisement.jobContent` (jobDescriptions[].title,
  company{name,website}, location). robots.txt allows the API (only the `/job-search/`
  UI is disallowed). Keyword filter is client-side. Source uses a `JsonPost` seam;
  `pipeline.build_live_scout` + `production_transports` extended with `http_post`.
- **opendata.swiss Zefix = SPARQL/LINDAS** (not a CSV bulk), same low-value registry
  data (no industry/website) — **Job-Room is strictly better for CH** (works now, has
  company websites), so the SPARQL loader is skipped.
- CH plan: **Job-Room (live) + ATS semi-auto seeds**. Zefix/opendata not needed.

## Sprint 13 — Scrapling crawler backend (stealth/JS)
Status: **complete** (offline 125 tests; scrapling is an optional extra, not in CI).

- The static `urllib` crawler missed JS-rendered / 403 SME sites (seen in the live
  brute-force run). **`sources/crawl/scrapling_fetcher.py`**: `ScraplingFetcher` wraps
  Scrapling's `StealthyFetcher`/`DynamicFetcher` as an `HttpGet` (`(url)->str` via
  `page.html_content`) → a **drop-in for `CareerPageCrawler`**. Lazy import + injectable
  `fetch_fn` seam → tested offline with no scrapling installed.
- `build_career_crawler()` uses Scrapling when the `scrape` extra is installed, else the
  static fallback. `brute_force_search` defaults to it. `ScraplingFetcher(**extra_opts)`
  passes through proxy / additional_args / wait_selector etc.
- **Verified LIVE** on `quotes.toscrape.com/js/` (JS-rendered): static urllib parsed **0**
  quotes; our `ScraplingFetcher` (DynamicFetcher/Chromium) rendered JS → **10** quotes.
- Activate: `uv pip install -e '.[scrape]'` then `scrapling install`. The official
  Scrapling Claude Code skill is installed at `~/.claude/skills/scrapling-official/`.

## Sprint 14 — The discovery engine (find unknown companies via search)
Status: **complete** (offline 128 tests; verified live — real Prague jobs, no names known).

The point of the agent is to find SME jobs the user *doesn't* know about; asking the
user for company names inverts that. Registry brute-force (ARES) yields ~0 (shells, no
industry filter) regardless of crawler quality. The fix:

- **`discovery/ats_search.py`** `AtsSearchDiscoverer`: searches the public ATS board
  domains (`site:jobs.personio.de praha`, `site:jobs.lever.co prague`, …) — every hit is
  a company **actively hiring on an ATS now**; the result URL carries the handle, so we
  pull its structured feed. No company names needed upfront. `keep_jobs_in_country`
  filters the cross-border results to the target market **by city** (description-matching
  leaked multinationals' German jobs in).
- **Verified LIVE (CZ)**: 4 Brave searches → 56 companies → ~1900 jobs → filtered to real
  Prague jobs at **gtowizard (Product Manager / Lead Designer), binance, contabo** — all
  discovered with zero prior knowledge. (vs ARES brute-force = 0.)
- Wired into `pipeline.build_live_scout(search_fn=...)` + `brave_search_fn(settings)` and
  the UI Live mode (with country filtering). 1 search = 1 Brave call (quota: 1000/mo).

## Sprint 15 — Supabase live (end-to-end persistence verified)
Status: **complete** (real stores against a real Supabase project, EU/Ireland region).

- Supabase project created (eu-west-1, Ireland = EU/GDPR-OK). `db/migrations/002_reset.sql`
  fixes a bad initial state (partial `jobs` table + missing tables + no service_role
  grants): DROP + recreate all 4 tables + `grant ... to service_role` + `notify pgrst`.
- **Verified LIVE** with the real `SupabaseJobStore` / `SupabaseApplicationStore` /
  `SupabaseObservability` (`supabase` py installed): jobs upsert+read, Tracker
  create→applied persisted, agent_runs + llm_events written. All 4 tables work.
- **TLS root cause (corrected — NOT a proxy):** cert issuers are real CAs (Google/Amazon).
  The failures were the classic macOS python.org issue — stdlib `ssl` has an empty CA store
  (`get_default_verify_paths` → missing cafile/capath), so `urllib` couldn't verify. **Fixed
  in `sources/http.py`**: `urllib_http`/`urllib_post` verify against the `certifi` bundle
  (`ssl.create_default_context(cafile=certifi.where())`); `certifi` added to base deps.
  httpx parts (supabase/openai/jina) already used certifi. Verified with verification ON
  (Job-Room urllib + Supabase httpx) — the app runs clean on this machine, no workaround.

## Sprint 16 — Jobs persist in the UI (Supabase fully wired)
Status: **complete** (128 tests; verified live, then DB cleaned).

- UI `_job_store()` → `SupabaseJobStore` when configured. `_load_jobs` (Live mode) now
  persists the **in-country** jobs (after `keep_jobs_in_country`) so the `jobs` table
  isn't flooded with cross-border ATS-search results. Country filter now applies whenever
  a country is set (was gated on Brave). Apps already persist via `_application_store`.
- Verified live: a CH Scout run upserted 49 jobs to Supabase; test data then wiped (all
  tables back to 0). Supabase is now fully wired end-to-end (jobs + applications + runs).

## Sprint 17 — Yield up + deploy prep
Status: **complete** (128 tests; yield verified live; deploy entry boots).

- **Discovery yield** (`ats_search.py`): now searches `cities × ATS domains` (3 distinct
  major cities + Personio .de/.com + Greenhouse two domains + Lever + Recruitee = 18
  Brave calls/search). **Live result vs before**: CZ ~6 → **61 jobs / 13 companies**;
  CH ~30 → **432 jobs / 42 real Swiss companies** (e.g. comparis.ch). CH genuinely usable
  now. Job-Room page size 50 → 100.
- **Streamlit Cloud deploy prep**: `streamlit_app.py` (root entry, puts `src` on path),
  `requirements.txt` (runtime deps, no scrapling), secrets bridge in `app.py`
  (`st.secrets` → env), `.streamlit/secrets.toml.example`, `DEPLOY.md`, `.gitignore`
  excludes `.env`/secrets/`.cache`. Verified the entry boots via AppTest.

## Next
- Push to GitHub (private) — AFTER rotating all keys (DeepSeek/Brave/Jina/Supabase) since
  they were pasted in chat. Then deploy on Streamlit Cloud (main file `streamlit_app.py`).
- Optional: cache Brave search results to cut quota on repeat searches.
