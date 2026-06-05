# Deploying to Streamlit Community Cloud

Streamlit Cloud deploys **from a GitHub repo**, so the project must be on GitHub first.

## ⚠️ Before pushing — secrets

- **Never commit secrets.** `.env` and `.streamlit/secrets.toml` are gitignored.
- The keys used during development were pasted in chat — **rotate all of them** before
  going public: DeepSeek, Brave, Jina, and especially the **Supabase `service_role`** key
  (it bypasses Row Level Security — full DB access).
- A public repo + a leaked service_role key = anyone can read/write your database.

## Steps

1. **Push to GitHub** (private repo recommended):
   ```bash
   git init && git add . && git commit -m "EU Job Agent"
   gh repo create eu-job-agent --private --source=. --push   # or create on github.com and push
   ```
   Confirm `.env` is NOT in the commit: `git ls-files | grep -i env` should show only
   `.env.example` / `.streamlit/secrets.toml.example`.

2. **Create the app** at https://share.streamlit.io → New app → pick the repo.
   - **Main file path**: `streamlit_app.py`
   - **Python version**: 3.11

3. **Add secrets** in the app's *Settings → Secrets* (TOML). Use the real, rotated keys
   from `.streamlit/secrets.toml.example`. `streamlit_app.py` mirrors them into the
   environment so `config.py` reads them.

4. **Supabase**: the schema is already applied (`db/migrations/001_init.sql` /
   `002_reset.sql`). The deployed app reads/writes the same project via `SUPABASE_URL` /
   `SUPABASE_KEY` secrets.

## Notes

- `requirements.txt` (repo root) is what Cloud installs — runtime deps only. Scrapling is
  excluded (Live mode doesn't crawl career pages; Cloud can't run Playwright browsers).
- Quota: each Live search ≈ 18 Brave calls (3 cities × 6 ATS domains). Brave free tier is
  1000/month — tune `AtsSearchDiscoverer(cities=...)` if needed.
- Without LLM/Brave/Supabase secrets the app still runs (Demo mode, in-memory) and
  degrades gracefully.
