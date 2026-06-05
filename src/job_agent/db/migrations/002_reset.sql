-- One-time setup reset. Run this in the Supabase SQL Editor INSTEAD of 001_init.sql
-- when the schema is in a bad state (wrong columns / missing tables / missing grants).
-- It DROPS the four tables (safe during setup — no real data yet), recreates them with
-- the correct schema, grants access to the API roles, and reloads the PostgREST cache.

drop table if exists public.llm_events  cascade;
drop table if exists public.agent_runs   cascade;
drop table if exists public.applications cascade;
drop table if exists public.jobs         cascade;

create table public.jobs (
    id                 bigint generated always as identity primary key,
    source             text not null,
    external_id        text not null,
    title              text not null,
    company            text not null default '',
    country            text not null,
    city               text,
    track              text not null default 'private',
    source_type        text not null default 'unknown',
    languages_required text[] not null default '{}',
    salary_eur         integer,
    description        text not null default '',
    url                text,
    visa_signal        text not null default 'unknown',
    employment_type    text not null default 'full_time',
    scraped_at         timestamptz not null default now(),
    unique (source, external_id)
);
create index jobs_country_track_idx on public.jobs (country, track);

create table public.applications (
    id                text primary key,
    job_source        text not null,
    job_external_id   text not null,
    job_title         text not null,
    company           text not null default '',
    candidate_ref     text not null,
    status            text not null default 'new',
    cover_letter      text,
    created_at        timestamptz not null,
    applied_at        timestamptz,
    follow_up_at      timestamptz,
    history           jsonb not null default '[]'
);
create index applications_candidate_idx on public.applications (candidate_ref);

create table public.agent_runs (
    run_id        uuid primary key,
    agent_name    text not null,
    started_at    timestamptz not null,
    finished_at   timestamptz,
    status        text not null default 'running',
    error_message text
);

create table public.llm_events (
    id                bigint generated always as identity primary key,
    run_id            uuid references public.agent_runs (run_id) on delete set null,
    prompt_snippet    text,
    response_snippet  text,
    prompt_tokens     integer,
    completion_tokens integer,
    cost_usd          numeric,
    duration_ms       integer,
    created_at        timestamptz not null default now()
);

-- Grant the API roles access (the agent connects with the service_role key).
grant usage on schema public to service_role, anon, authenticated;
grant all privileges on all tables    in schema public to service_role;
grant all privileges on all sequences in schema public to service_role;

-- Make PostgREST pick up the new schema immediately.
notify pgrst, 'reload schema';
