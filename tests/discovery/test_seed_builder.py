"""Seed builder — known career URLs + semi-auto ATS-handle probing → verified seeds."""

from job_agent.discovery.seed_builder import (
    SeedEntry,
    build_seeds,
    handle_candidates,
    load_seeds,
    probe_ats_handles,
    save_seeds,
    verify_seed,
)
from job_agent.models.company import ATSPlatform

_PAGES = {
    "https://a.cz/careers": '<a href="https://acme.jobs.personio.de/">open roles</a>',
    "https://b.cz/jobs": 'apply via boards.greenhouse.io/bravo today',
    "https://c.cz/kariera": "<p>plain page, no ATS embedded</p>",
}
_PERSONIO = '<?xml version="1.0"?><workzag-jobs><position><id>1</id><name>DevOps</name></position></workzag-jobs>'


def test_build_seeds_fingerprints_and_reports_failures() -> None:
    entries = [
        SeedEntry("Acme", "CZ", "https://a.cz/careers", industry="IT"),
        SeedEntry("Bravo", "CZ", "https://b.cz/jobs"),
        SeedEntry("Plain", "CZ", "https://c.cz/kariera"),
    ]
    seeds, failed = build_seeds(entries, lambda url: _PAGES[url])

    assert {s.name for s in seeds} == {"Acme", "Bravo"}
    acme = next(s for s in seeds if s.name == "Acme")
    assert acme.ats.value == "personio" and acme.ats_handle == "acme"
    assert acme.discovered_via == "curated" and acme.careers_url == "https://a.cz/careers"
    assert failed == ["Plain"]  # no ATS detected


def test_build_seeds_isolates_unreachable_pages() -> None:
    def http(url: str) -> str:
        raise ConnectionError("timeout")

    seeds, failed = build_seeds([SeedEntry("X", "CZ", "https://x.cz")], http)
    assert seeds == [] and failed == ["X"]


def test_verify_seed_counts_jobs() -> None:
    [acme], _ = build_seeds([SeedEntry("Acme", "CZ", "https://a.cz/careers")],
                            lambda url: _PAGES["https://a.cz/careers"])
    assert verify_seed(acme, lambda url: _PERSONIO) == 1


# --- semi-automatic collection: derive handles from names, probe ATS feeds -----


def test_handle_candidates_slugifies_and_variants() -> None:
    cands = handle_candidates(["Acme Software s.r.o."], country="CZ", industry="IT")
    handles = {c.handle for c in cands}
    assert handles == {"acmesoftware", "acme-software"}  # legal suffix stripped, 2 variants
    assert all(c.country == "CZ" and c.name == "Acme Software s.r.o." for c in cands)


_GREENHOUSE = '{"jobs": [{"id": 1, "title": "Engineer", "location": {"name": "Praha"}}]}'


def test_probe_keeps_only_live_handles() -> None:
    def http(url: str) -> str:
        if "acme.jobs.personio.de" in url:
            return _PERSONIO
        if "boards/bravo/jobs" in url:
            return _GREENHOUSE
        raise RuntimeError("404")  # every other probe is a dead handle

    cands = [
        # 'acme' resolves on Personio; 'bravo' only on Greenhouse; 'ghost' nowhere.
        *handle_candidates(["acme"], "CZ"),
        *handle_candidates(["bravo"], "CZ"),
        *handle_candidates(["ghost"], "CZ"),
    ]
    seeds = probe_ats_handles(cands, http)

    by_handle = {s.ats_handle: s.ats for s in seeds}
    assert by_handle == {"acme": ATSPlatform.personio, "bravo": ATSPlatform.greenhouse}
    assert all(s.discovered_via == "ats_probe" for s in seeds)


def test_save_and_load_seeds_roundtrip(tmp_path) -> None:
    seeds = probe_ats_handles(handle_candidates(["acme"], "CZ", "IT"),
                              lambda url: _PERSONIO if "personio" in url else _GREENHOUSE)
    path = tmp_path / "seeds.json"
    save_seeds(seeds, path)
    loaded = load_seeds(path)
    assert load_seeds(tmp_path / "missing.json") == []
    assert [s.ats_handle for s in loaded] == [s.ats_handle for s in seeds]
    assert loaded[0].ats is ATSPlatform.personio  # enum restored from JSON

