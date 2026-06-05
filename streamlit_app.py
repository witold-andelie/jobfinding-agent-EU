"""Streamlit Community Cloud entry point.

Cloud runs the app from the repo root, but the package lives under ``src/``. This
shim puts ``src`` on the path and then renders the dashboard. Point the Streamlit
Cloud app at this file (``streamlit_app.py``).
"""

import pathlib
import sys

sys.path.insert(0, str(pathlib.Path(__file__).parent / "src"))

import job_agent.ui.app  # noqa: E402,F401  -- importing the module renders the Streamlit app
