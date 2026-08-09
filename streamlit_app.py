"""Streamlit Community Cloud entry point.

Cloud runs the app from the repo root, but the package lives under ``src/``. We
execute ``src/job_agent/ui/app.py`` *as a script* via ``runpy`` rather than
``import job_agent.ui.app``. The import path cached the module in ``sys.modules``
and, on every sidebar rerun, re-importing a module that calls Streamlit top-level
widgets caused Community Cloud to white-screen. ``runpy.run_path`` executes the
script fresh each time (no module caching), mirroring inline behaviour.
"""
import pathlib
import runpy
import sys

sys.path.insert(0, str(pathlib.Path(__file__).parent / "src"))

runpy.run_path(str(pathlib.Path(__file__).parent / "src" / "job_agent" / "ui" / "app.py"),
               run_name="__main__")