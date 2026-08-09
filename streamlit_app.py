"""Streamlit Community Cloud entry point.

Executes ``src/job_agent/ui/app.py`` via ``runpy`` rather than
``import job_agent.ui.app`` to avoid the module-cache wedge that blanked the page
on every sidebar interaction on Community Cloud.
"""
import pathlib
import runpy
import sys

# Diagnostic: surface which site-packages dir resolves `openai`, before app.py runs.
# Shows up in Cloud Logs as a printed line; helps pinpoint why the LLM button fails.
try:
    import openai  # noqa: E402
    print(f"[diag] openai OK: {openai.__file__}", flush=True)  # noqa: T201
except ModuleNotFoundError as exc:
    print(f"[diag] openai MISSING: {exc}", flush=True)  # noqa: T201
    print(f"[diag] sys.path = {sys.path}", flush=True)  # noqa: T201

sys.path.insert(0, str(pathlib.Path(__file__).parent / "src"))

runpy.run_path(str(pathlib.Path(__file__).parent / "src" / "job_agent" / "ui" / "app.py"),
               run_name="__main__")