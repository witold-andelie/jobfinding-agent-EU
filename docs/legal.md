# Legal & compliance posture (brute-force crawling)

Mirrors the reference project's discipline (it excluded StepStone over ToS). The
brute-force registry→crawl path must stay within these lines:

## Business registers
- **CZ — ARES**: open government data, free, no auth. Public REST API; use a clear
  User-Agent and a sane request rate.
- **CH — Zefix**: public name index, but the REST API **requires a registered
  account** (Basic auth). Respect their usage terms and rate limits.
- Registers return company identity, not websites — domain resolution is a separate
  step (a search API or heuristic), and must itself respect that provider's terms.

## Excluded sources (ToS / robots.txt)
- **StepStone** — robots.txt + ToS forbid scraping (carried over from the reference).
- **jobup.ch / jobs.ch (JobCloud)** — their JSON search API lives under `/api/`, which
  `robots.txt` explicitly **Disallows** (`Disallow: /api/`). Technically reachable, but
  off-limits by the same principle as StepStone. Use the official **Job-Room** (SECO)
  source + ATS feeds for Swiss coverage instead.

## Crawling company career pages (Layer 3)
- **Respect `robots.txt`** — use `RobotsTxtChecker` (reads + enforces robots.txt via
  the stdlib parser), not just the permissive default. Plus each site's Terms of Service.
- **Rate-limit** and identify the crawler (`RateLimiter` seam + User-Agent).
- Prefer structured **ATS feeds** over HTML scraping when an ATS is detected.
- Crawl only publicly available vacancy pages; do not bypass auth or paywalls.

## GDPR
- Store company/job data, not personal data of applicants beyond the user's own CV.
- The user's CV is processed only to match/generate their application; keep it under
  the user's control. Apply retention limits to scraped jobs.
- Submission stays **manual** — the agent prepares applications; the user sends them.
