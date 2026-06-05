# EU Job Agent

A job-search agent for **junior international graduates** (need-not-mandatory visa
support) who want to build a career in Europe — deliberately covering the
**small/medium employers and international organisations that do *not* recruit
through LinkedIn**.

Architecture patterns (dependency injection, multi-source Scout, observability,
offline-first testability) are adapted from the W-HS `job-agent-whs` reference
project; the domain model, source coverage, and the visa-feasibility engine are
new.

## Two tracks

- **Track A — private / SME**: legal route is national work authorisation
  (EU Blue Card, post-study job-seeker permits, **local-degree exemptions**).
  Visa sponsorship is a *soft* signal, never a hard filter.
- **Track B — international organisations**: UN / EU / NGO roles + internships /
  traineeships / JPO. Different legal status (often self-granted), very
  competitive at junior level.

## Visa feasibility, not a yes/no filter

The core insight: whether a candidate can take a job depends on
`(nationality, degree-country, field, salary) × job-country`. A non-EU graduate
**holding a local degree** is often exempt from employer sponsorship entirely
(e.g. CZ, PL: no work permit; DE/AT/CH: priority-check / facilitation). So jobs
that never mention "visa sponsorship" are still fully viable. See
`src/job_agent/visa/`.

> The encoded immigration rules are a starting point and must be verified against
> official sources before being shown to a user as advice.

## Status

Offline-first. No live LLM / DB / network calls yet — everything runs under
`pytest`. Country coverage target: DE, NL, FR, AT, BE, LU, CZ, PL, DK, IT, CH
(+ international-org hubs).

## Setup

```bash
uv sync --extra dev
uv run pytest
```
