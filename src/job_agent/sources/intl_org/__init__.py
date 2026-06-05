"""Layer — international organisations (Track B).

Unlike Track A (company → ATS feed), Track B is board-shaped: query a board for
roles across many organisations. ReliefWeb is the first adapter because it has a
real, auth-free public JSON API; UN Careers, Impactpool, EPSO, EuroBrussels follow
the same shape. Geneva/Vienna/Brussels hubs are reached via the query's country.
"""

from job_agent.sources.intl_org.reliefweb import (
    ReliefWebAdapter,
    ReliefWebSource,
    fetch_intl_org_jobs,
)

__all__ = ["ReliefWebAdapter", "ReliefWebSource", "fetch_intl_org_jobs"]
