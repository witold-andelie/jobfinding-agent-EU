"""ATS fingerprinting — the 'broad search' discovery route."""

from job_agent.discovery import AtsDetectDiscoverer, DiscoveryQuery, detect_ats
from job_agent.models.company import ATSPlatform, CompanyTarget


def test_detect_from_urls() -> None:
    assert detect_ats("https://acme.jobs.personio.de/") == (ATSPlatform.personio, "acme")
    assert detect_ats("boards.greenhouse.io/acme") == (ATSPlatform.greenhouse, "acme")
    assert detect_ats("https://jobs.lever.co/acme/123") == (ATSPlatform.lever, "acme")
    assert detect_ats("https://acme.recruitee.com/") == (ATSPlatform.recruitee, "acme")
    assert detect_ats("https://example.com/careers") == (ATSPlatform.unknown, None)


def test_detect_from_embedded_html() -> None:
    html = '<a href="https://greatco.jobs.personio.com/recruiting">Open roles</a>'
    assert detect_ats(html) == (ATSPlatform.personio, "greatco")


def test_discoverer_enriches_company_with_detected_ats() -> None:
    company = CompanyTarget(
        name="Moravia Cloud s.r.o.",
        country="CZ",
        industry="IT / Cloud",
        careers_url="https://moraviacloud.jobs.personio.de/",
    )
    # http_get returns the careers page; here the URL itself carries the fingerprint.
    discoverer = AtsDetectDiscoverer([company], http_get=lambda url: url)
    [enriched] = discoverer.discover(DiscoveryQuery(country="CZ", industry="IT"))

    assert enriched.ats is ATSPlatform.personio
    assert enriched.ats_handle == "moraviacloud"
    assert enriched.discovered_via == "ats_crawl"
