# Streamlit Setup

## App Settings

Create the Streamlit Community Cloud app from this repository with:

- **Main file path:** `streamlit_app.py`
- **Python version:** `3.11`

Open **Settings -> Secrets** and paste TOML values using real, rotated credentials:

```toml
LLM_PROVIDER = "opencode"
LLM_API_KEY = "replace-with-opencode-key"
LLM_BASE_URL = "https://opencode.ai/zen/go/v1/responses"
LLM_MODEL = "gpt-5.6-luna"
LLM_API_MODE = "responses"

EMBEDDING_PROVIDER = "jina"
EMBEDDING_API_KEY = "replace-with-jina-key"
EMBEDDING_BASE_URL = "https://api.jina.ai/v1"
EMBEDDING_MODEL = "jina-embeddings-v3"

BRAVE_API_KEY = "replace-with-brave-key"

SUPABASE_URL = "https://your-project.supabase.co"
SUPABASE_KEY = "replace-with-supabase-server-key"
```

`SUPABASE_KEY` is used by the server-side Streamlit app. Do not use the browser
publishable key for this setting. EURES, public ATS feeds, and Job-Room do not need
additional credentials.

## Supabase

Apply the schema in `src/job_agent/db/migrations/001_init.sql`. If the project was
created from an earlier broken schema, use `002_reset.sql` instead as documented by
the deployment owner. The app uses these tables:

- `jobs`
- `applications`
- `agent_runs`
- `llm_events`

The app falls back to in-memory application storage when Supabase settings are absent.

## Local Run

```powershell
uv pip install -e ".[llm,ui,scrape]"
python -m playwright install chromium
streamlit run streamlit_app.py
```

Without LLM or Brave credentials, Demo mode and deterministic matching still work.
Without Scrapling browser binaries, the crawler falls back to the static HTTP fetcher.

## Security

- Never commit `.env` or `.streamlit/secrets.toml`.
- Rotate any key that has appeared in chat, logs, screenshots, or a public repository.
- Prefer a Supabase server-side key with minimum required database privileges.
- Do not place provider keys in frontend code or publishable client configuration.
