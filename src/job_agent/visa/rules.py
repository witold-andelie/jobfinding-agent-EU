"""Per-country immigration rules, encoded as data.

SCOPE: the legal route for a *non-EU/EEA/Swiss* graduate to work in each target
country. EU/EEA/Swiss nationals have free movement and are handled directly in
the engine without consulting this table.

The single most important axis is the **local degree**: a candidate whose highest
degree was granted *by the country they want to work in*. Across Europe a local
degree ranges from "removes the work-permit requirement entirely" (CZ, PL) to
"waives the labour-market priority check / lowers thresholds" (DE, AT, NL, CH).

WARNING: these values are an engineering starting point compiled from public
information and WILL drift as immigration law changes. They must be verified
against official sources before being surfaced to a user as advice. Each rule
carries a ``source_hint`` for exactly that follow-up.
"""

from dataclasses import dataclass, field


@dataclass(frozen=True)
class CountryVisaRule:
    country: str  # ISO-2
    name: str

    # A non-EU graduate holding a LOCAL degree needs no employer work permit at
    # all — free access to the labour market.
    local_degree_no_work_permit: bool = False

    # A non-EU graduate holding a LOCAL degree still needs a permit, but the
    # labour-market priority check (proving no EU candidate exists) is waived and
    # the employer's burden is light.
    local_degree_waives_priority_check: bool = False

    # Months a fresh local graduate may stay to look for qualified work.
    post_study_job_search_months: int | None = None

    # EU Blue Card route exists for graduate-level jobs above a salary threshold.
    blue_card_available: bool = True

    # How hard it is for a non-EU junior WITHOUT a local degree: "low"|"medium"|"high".
    difficulty_without_local_degree: str = "medium"

    notes: str = ""
    source_hints: list[str] = field(default_factory=list)


# Ordered roughly by visa-friendliness for the target persona.
COUNTRY_RULES: dict[str, CountryVisaRule] = {
    "DE": CountryVisaRule(
        country="DE",
        name="Germany",
        local_degree_waives_priority_check=True,
        post_study_job_search_months=18,
        difficulty_without_local_degree="low",
        notes="German degree: 18-month job-seeker permit; matching job gets a "
        "residence permit with no priority check. Blue Card thresholds lower for "
        "STEM/IT shortage occupations. Opportunity Card (Chancenkarte, 2024) is a "
        "points-based job-seeker route even without a local degree.",
        source_hints=["§18b/§20 AufenthG", "make-it-in-germany.com"],
    ),
    "NL": CountryVisaRule(
        country="NL",
        name="Netherlands",
        local_degree_waives_priority_check=True,
        post_study_job_search_months=12,
        difficulty_without_local_degree="low",
        notes="Orientation year ('zoekjaar') within 3 years of graduating. Highly "
        "Skilled Migrant scheme has a REDUCED salary threshold for recent grads / "
        "search-year holders; employer must be an IND recognised sponsor.",
        source_hints=["IND highly skilled migrant", "zoekjaar"],
    ),
    "FR": CountryVisaRule(
        country="FR",
        name="France",
        local_degree_waives_priority_check=True,
        post_study_job_search_months=12,
        difficulty_without_local_degree="medium",
        notes="APS (autorisation provisoire de séjour) up to 12 months for master's "
        "graduates; change of status to 'salarié' or 'passeport talent' is "
        "facilitated with a French degree.",
        source_hints=["APS recherche d'emploi", "Passeport Talent"],
    ),
    "AT": CountryVisaRule(
        country="AT",
        name="Austria",
        local_degree_waives_priority_check=True,
        post_study_job_search_months=12,
        difficulty_without_local_degree="medium",
        notes="Graduates of Austrian universities get a 12-month job-seeker permit "
        "and a Red-White-Red Card with reduced criteria (no points test, lower "
        "minimum salary for graduates).",
        source_hints=["Red-White-Red Card Graduate", "migration.gv.at"],
    ),
    "BE": CountryVisaRule(
        country="BE",
        name="Belgium",
        local_degree_waives_priority_check=True,
        post_study_job_search_months=12,
        difficulty_without_local_degree="medium",
        notes="Search-year residence after graduating from a Belgian institution; "
        "otherwise the single-permit (combined work+residence) route. Brussels is "
        "also the densest international-organisation market (EU institutions, NATO).",
        source_hints=["Belgium search year", "single permit"],
    ),
    "LU": CountryVisaRule(
        country="LU",
        name="Luxembourg",
        local_degree_waives_priority_check=True,
        post_study_job_search_months=12,
        difficulty_without_local_degree="medium",
        notes="Graduates may stay to seek work; salaried-worker authorisation "
        "otherwise. Highly international, multilingual labour market; large EU-"
        "institution employer base (CJEU, EIB, Court of Auditors, Eurostat).",
        source_hints=["guichet.lu salaried worker"],
    ),
    "CZ": CountryVisaRule(
        country="CZ",
        name="Czechia",
        local_degree_no_work_permit=True,
        post_study_job_search_months=9,
        difficulty_without_local_degree="medium",
        notes="Graduates of an accredited Czech school have FREE access to the "
        "labour market — no work/employment permit needed (employer sponsorship is "
        "not required). An Employee Card / residence permit is still needed for "
        "residence, but without a labour-market test.",
        source_hints=["MPSV free labour market access graduates", "Employee Card"],
    ),
    "PL": CountryVisaRule(
        country="PL",
        name="Poland",
        local_degree_no_work_permit=True,
        post_study_job_search_months=9,
        difficulty_without_local_degree="medium",
        notes="Foreigners who completed full-time (stationary) studies in Poland are "
        "EXEMPT from the work-permit requirement. Large shared-service-centre (SSC) "
        "market hiring internationally.",
        source_hints=["Act on employment of foreigners — work permit exemptions"],
    ),
    "DK": CountryVisaRule(
        country="DK",
        name="Denmark",
        local_degree_waives_priority_check=True,
        post_study_job_search_months=36,
        difficulty_without_local_degree="medium",
        notes="Generous post-study job-search period for Danish-degree holders; "
        "Pay Limit / Positive List schemes otherwise. Copenhagen 'UN City' hub.",
        source_hints=["nyidanmark.dk establishment card", "Positive List"],
    ),
    "IT": CountryVisaRule(
        country="IT",
        name="Italy",
        local_degree_waives_priority_check=True,
        post_study_job_search_months=12,
        difficulty_without_local_degree="high",
        notes="Conversion of a study permit to a work permit for graduates of "
        "Italian universities; general work immigration is quota-bound (decreto "
        "flussi). Rome hosts the UN food agencies (FAO/WFP/IFAD).",
        source_hints=["conversione permesso studio-lavoro", "decreto flussi"],
    ),
    "CH": CountryVisaRule(
        country="CH",
        name="Switzerland",
        local_degree_waives_priority_check=True,  # Art. 21(3) FNIA, qualified jobs
        post_study_job_search_months=6,
        blue_card_available=False,  # not in the EU; no EU Blue Card
        difficulty_without_local_degree="high",
        notes="NOT in the EU. For non-EU/EFTA nationals, permits are quota-bound and "
        "subject to a strict priority rule. A SWISS degree is the key unlock: holders "
        "get a 6-month search permit and are exempt from the priority rule for jobs "
        "of high scientific/economic interest. Without a Swiss degree, junior roles "
        "are very hard — manage expectations. Geneva international organisations "
        "(Track B) bypass this entirely.",
        source_hints=["Art. 21 para 3 FNIA", "SEM working in Switzerland non-EU"],
    ),
}
