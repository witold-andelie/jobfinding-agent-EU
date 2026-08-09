"""Streamlit Community Cloud entry point.

Executes ``src/job_agent/ui/app.py`` via ``runpy`` rather than
``import job_agent.ui.app`` to avoid the module-cache wedge that blanked the page
on every sidebar interaction on Community Cloud.
"""
import importlib
import pathlib
import runpy
import sys
import time

import streamlit as st

# Wait for Streamlit to finish "Processing dependencies..." on Community Cloud.
# The app script runs BEFORE pip install completes, so imports of freshly-installed
# packages fail on the first boot. Poll for `openai` to become importable.
_DEADLINE = time.time() + 180


def _openai_ready() -> bool:
    try:
        importlib.import_module("openai")  # noqa: S404,F401
        return True
    except ModuleNotFoundError:
        return False


if not _openai_ready():
    st.info("Installing dependencies… (first boot after a deploy can take a minute)")
    placeholder = st.empty()
    while time.time() < _DEADLINE:
        if _openai_ready():
            placeholder.empty()
            break
        time.sleep(2)
    else:
        placeholder.empty()
        # Last-resort: list what's actually in venv site-packages for debugging.
        import os
        for p in sys.path:
            if "site-packages" in p:
                try:
                    entries = sorted(os.listdir(p))
                except OSError:
                    continue
                print(f"[diag] {p} openai-like: {[e for e in entries if 'openai' in e.lower()]}", flush=True)  # noqa: T201
                st.warning("Dependencies did not finish installing; check Manage app → Logs.")

sys.path.insert(0, str(pathlib.Path(__file__).parent / "src"))

runpy.run_path(str(pathlib.Path(__file__).parent / "src" / "job_agent" / "ui" / "app.py"),
               run_name="__main__")