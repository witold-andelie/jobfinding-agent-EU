"""Supabase-backed stores: serialization, dedupe, observability, Scout drop-in."""

from job_agent.agents import ScoutAgent, ScoutQuery
from job_agent.db.client import SupabaseClient
from job_agent.discovery import DiscoveryQuery, SeedDiscoverer
from job_agent.models.candidate import Track
from job_agent.models.company import ATSPlatform, CompanyTarget
from job_agent.models.job import EmploymentType, Job, VisaSignal
from job_agent.observability.supabase import SupabaseObservability
from job_agent.persistence.supabase import SupabaseJobStore


def _job(ext: str) -> Job:
    return Job(source="personio", external_id=ext, title="Dev", company="C", country="CZ",
               track=Track.private, visa_signal=VisaSignal.likely,
               employment_type=EmploymentType.internship)


def test_jobstore_upserts_deduped_rows_with_serialized_enums(fake_supabase) -> None:
    store = SupabaseJobStore(SupabaseClient(client=fake_supabase))
    n = store.upsert_jobs([_job("1"), _job("1"), _job("2")])  # one duplicate

    assert n == 2
    assert len(fake_supabase.calls) == 1
    call = fake_supabase.calls[0]
    assert call["table"] == "jobs" and call["op"] == "upsert"
    assert call["on_conflict"] == "source,external_id"
    assert len(call["payload"]) == 2  # deduped
    row = call["payload"][0]
    assert row["visa_signal"] == "likely"        # enum -> str
    assert row["employment_type"] == "internship"
    assert row["track"] == "private"


def test_jobstore_empty_does_not_call_db(fake_supabase) -> None:
    store = SupabaseJobStore(SupabaseClient(client=fake_supabase))
    assert store.upsert_jobs([]) == 0
    assert fake_supabase.calls == []


def test_observability_records_run_and_event(fake_supabase) -> None:
    from job_agent.observability import start_run

    obs = SupabaseObservability(SupabaseClient(client=fake_supabase))
    ctx = start_run("scout")
    obs.insert_run(ctx)
    obs.finish_run(ctx.run_id, "success")
    obs.insert_llm_event(run_id=ctx.run_id, prompt_snippet="p", response_snippet="r",
                         prompt_tokens=10, completion_tokens=5, duration_ms=120, cost_usd=0.0001)

    tables = [c["table"] for c in fake_supabase.calls]
    assert tables == ["agent_runs", "agent_runs", "llm_events"]
    assert fake_supabase.calls[1]["op"] == "update"
    assert fake_supabase.calls[1]["filters"] == [("run_id", ctx.run_id)]
    assert fake_supabase.calls[2]["payload"]["cost_usd"] == 0.0001


def test_supabase_stores_are_drop_in_for_scout(fake_supabase) -> None:
    db = SupabaseClient(client=fake_supabase)
    company = CompanyTarget(name="Co", country="CZ", ats=ATSPlatform.personio, ats_handle="co")
    xml = '<?xml version="1.0"?><workzag-jobs><position><id>1</id><name>Dev</name></position></workzag-jobs>'

    agent = ScoutAgent(
        http_get=lambda url: xml,
        discoverers=[SeedDiscoverer([company])],
        store=SupabaseJobStore(db),
        obs=SupabaseObservability(db),
    )
    result = agent.run(ScoutQuery(DiscoveryQuery(country="CZ")))

    assert result.stored == 1
    # Scout wrote: agent_runs insert + jobs upsert + agent_runs update (finish).
    tables = [c["table"] for c in fake_supabase.calls]
    assert "jobs" in tables and tables.count("agent_runs") == 2
