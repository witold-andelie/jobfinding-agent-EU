"""Streamlit Community Cloud entry point.

Executes ``src/job_agent/ui/app.py`` via ``runpy`` rather than
``import job_agent.ui.app`` to avoid the module-cache wedge that blanked the page
on every sidebar interaction on Community Cloud.
"""
import pathlib
import runpy
import sys

# Diagnostic: list what is actually in the venv site-packages so we can see whether
# openai was installed by pip (and what else is / isn't there).
import os  # noqa: E402
print("[diag] === site-packages contents (openai-ish) ===", flush=True)  # noqa: T201
for p in sys.path:
    if "site-packages" in p:
        try:
            entries = sorted(os.listdir(p))
        except OSError as exc:
            print(f"[diag] {p}: {exc}", flush=True)  # noqa: T201
            continue
        openai_like = [e for e in entries if "openai" in e.lower()]
        print(f"[diag] {p}", flush=True)  # noqa: T201
        print(f"[diag]   openai-like: {openai_like}", flush=True)  # noqa: T201
        print(f"[diag]   total entries: {len(entries)}", flush=True)  # noqa: T201
        print(f"[diag]   first 30: {entries[:30]}", flush=True)  # noqa: T201

sys.path.insert(0, str(pathlib.Path(__file__).parent / "src"))

runpy.run_path(str(pathlib.Path(__file__).parent / "src" / "job_agent" / "ui" / "app.py"),
               run_name="__main__")