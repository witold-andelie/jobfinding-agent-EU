-- EU Job Agent schema (adapted from job-agent-whs 001_init.sql for this product's model).
-- pgvector is deferred (DeepSeek has no embeddings); add it when a 3rd-party embedder lands.

create table if not exists jobs (
    id                 bigint generated always as identity primary key,
    source             text not null,
    external_id        text not null,
    title              text not null,
    company            text not null default '',
    country            text not null,            -- ISO-2
    city               text,
    track              text not null default 'private',     -- private | intl_org
    source_type        text not null default 'unknown',     -- pes | eures | niche | intl_org
    languages_required text[] not null default '{}',
    salary_eur         integer,
    description        text not null default '',
    url                text,
    visa_signal        text not null default 'unknown',      -- explicit_yes|likely|unknown|explicit_no
    employment_type    text not null default 'full_time',
    scraped_at         timestamptz not null default now(),
    unique (source, external_id)                 -- dedupe key (matches InMemoryJobStore)
);
create index if not exists jobs_country_track_idx on jobs (country, track);

-- Applications / Tracker. Denormalised (jobs may originate in-memory, not in `jobs`);
-- id is the app-generated UUID so SupabaseApplicationStore is a drop-in for the
-- in-memory store and matches the Application model field-for-field.
create table if not exists applications (
    id                text primary key,          -- Application.id (uuid)
    job_source        text not null,
    job_external_id   text not null,
    job_title         text not null,
    company           text not null default '',
    candidate_ref     text not null,             -- opaque candidate identifier
    status            text not null default 'new', -- new|applied|interview|offer|accepted|rejected|withdrawn
    cover_letter      text,
    created_at        timestamptz not null,
    applied_at        timestamptz,
    follow_up_at      timestamptz,
    history           jsonb not null default '[]'
);
create index if not exists applications_candidate_idx on applications (candidate_ref);

-- Observability (mirrors the reference's agent_runs / llm_events).
create table if not exists agent_runs (
    run_id        uuid primary key,
    agent_name    text not null,
    started_at    timestamptz not null,
    finished_at   timestamptz,
    status        text not null default 'running',
    error_message text
);

create table if not exists llm_events (
    id                bigint generated always as identity primary key,
    run_id            uuid references agent_runs (run_id) on delete set null,
    prompt_snippet    text,
    response_snippet  text,
    prompt_tokens     integer,
    completion_tokens integer,
    cost_usd          numeric,
    duration_ms       integer,
    created_at        timestamptz not null default now()
);
