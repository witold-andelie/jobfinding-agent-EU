"""Registry clients (CZ ARES / CH Zefix) + RegistryDiscoverer — offline, real shapes."""

from job_agent.discovery import (
    AresClient,
    DiscoveryQuery,
    RegistryDiscoverer,
    ZefixClient,
)

# ARES /vyhledat response, matching the live shape probed in 2026.
_ARES = """{"pocetCelkem": 2, "ekonomickeSubjekty": [
  {"ico": "27082440", "obchodniJmeno": "Acme Software s.r.o.",
   "sidlo": {"nazevObce": "Praha"}, "czNace": ["620200"]},
  {"obchodniJmeno": "Brno DataWorks a.s.", "sidlo": {"nazevObce": "Brno"}, "czNace": []}
]}"""

# Zefix firm/search.json response (documented shape).
_ZEFIX = """{"list": [
  {"name": "Lac Léman Software SA", "uid": "CHE-123.456.789", "legalSeat": "Genève"}
]}"""


def _post(mapping):
    def _p(url, body, headers=None):
        for needle, resp in mapping.items():
            if needle in url:
                return resp
        raise AssertionError(f"unexpected POST: {url}")
    return _p


def test_ares_parses_subjects() -> None:
    recs = AresClient(_post({"ares.gov.cz": _ARES})).search(keyword="software")
    assert [r.name for r in recs] == ["Acme Software s.r.o.", "Brno DataWorks a.s."]
    assert recs[0].country == "CZ" and recs[0].registry_id == "27082440"
    assert recs[0].city == "Praha" and recs[0].nace == ["620200"]


def test_zefix_parses_and_passes_auth_header() -> None:
    seen = {}

    def _p(url, body, headers=None):
        seen["headers"] = headers
        return _ZEFIX

    recs = ZefixClient(_p, auth_header="Basic xyz").search(keyword="software")
    assert recs[0].name == "Lac Léman Software SA" and recs[0].country == "CH"
    assert recs[0].city == "Genève"
    assert seen["headers"] == {"Authorization": "Basic xyz"}


def test_discoverer_routes_by_country() -> None:
    ares = AresClient(_post({"ares.gov.cz": _ARES}))
    zefix = ZefixClient(_post({"zefix.admin.ch": _ZEFIX}))
    disc = RegistryDiscoverer([ares, zefix])

    cz = disc.discover(DiscoveryQuery(country="CZ", industry="software"))
    assert {c.country for c in cz} == {"CZ"} and len(cz) == 2
    assert all(c.discovered_via == "registry" and c.website is None for c in cz)

    ch = disc.discover(DiscoveryQuery(country="CH", industry="software"))
    assert {c.country for c in ch} == {"CH"}
