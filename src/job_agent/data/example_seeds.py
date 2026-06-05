"""Illustrative seed companies for the first demos.

NOTE: these are representative examples to exercise the pipeline. The names and ATS
handles are placeholders — real seed lists are built via the discovery layer
(registry ingestion + ATS fingerprinting) and must be verified before use.
"""

from job_agent.models.company import ATSPlatform, CompanyTarget

# Track A — Czech IT SMEs. Some have a known ATS (fetchable now), one only a
# careers URL (to be enriched by AtsDetectDiscoverer).
CZECH_IT_SEEDS: list[CompanyTarget] = [
    CompanyTarget(
        name="Vltava Software s.r.o.",
        country="CZ",
        industry="IT / Software",
        ats=ATSPlatform.personio,
        ats_handle="vltavasoftware",
        discovered_via="seed",
    ),
    CompanyTarget(
        name="Brno DataWorks a.s.",
        country="CZ",
        industry="IT / Data",
        ats=ATSPlatform.greenhouse,
        ats_handle="brnodataworks",
        discovered_via="seed",
    ),
    CompanyTarget(
        name="Moravia Cloud s.r.o.",
        country="CZ",
        industry="IT / Cloud",
        careers_url="https://moraviacloud.jobs.personio.de/",  # ATS to be detected
        discovered_via="seed",
    ),
]

# Track A — Switzerland across industries, Geneva-weighted. Switzerland is NOT in
# EURES, so it needs its own Layer-1 boards (jobs.ch nationwide; jobup.ch for
# Geneva / French-speaking Romandie) plus these ATS-fetchable employers. The first
# block is the international-relations-adjacent market a Geneva IR graduate targets.
SWISS_SEEDS: list[CompanyTarget] = [
    # — IR-adjacent (NGOs, global health, public affairs, think tanks, trading) —
    CompanyTarget(name="Léman Humanitarian Network", country="CH",
                  industry="International Affairs / NGO", ats=ATSPlatform.recruitee,
                  ats_handle="lemanhumanitarian"),
    CompanyTarget(name="Geneva Global Health Alliance", country="CH",
                  industry="Global Health / Policy", ats=ATSPlatform.personio,
                  ats_handle="genevaglobalhealth"),
    CompanyTarget(name="Rhône Public Affairs SA", country="CH",
                  industry="Public Affairs / Communications", ats=ATSPlatform.personio,
                  ats_handle="rhonepublicaffairs"),
    CompanyTarget(name="Alpine Policy Institute", country="CH",
                  industry="Think Tank / Research", ats=ATSPlatform.lever,
                  ats_handle="alpinepolicy"),
    CompanyTarget(name="Genève Commodities Trading SA", country="CH",
                  industry="Commodity Trading / Sustainability", ats=ATSPlatform.greenhouse,
                  ats_handle="genevacommodities"),
    # — Broader Swiss industries —
    CompanyTarget(name="Basel LifeSciences AG", country="CH",
                  industry="Pharma / Life Sciences", ats=ATSPlatform.personio,
                  ats_handle="basellifesciences"),
    CompanyTarget(name="Zürich Capital Partners AG", country="CH",
                  industry="Banking / Finance", ats=ATSPlatform.greenhouse,
                  ats_handle="zurichcapital"),
    CompanyTarget(name="Lac Léman Software SA", country="CH",
                  industry="IT / Software", ats=ATSPlatform.personio,
                  ats_handle="lacleman"),
    CompanyTarget(name="Jura Precision SA", country="CH",
                  industry="Manufacturing / Watchmaking", ats=ATSPlatform.personio,
                  ats_handle="juraprecision"),
]
