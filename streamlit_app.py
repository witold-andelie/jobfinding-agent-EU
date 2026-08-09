"""bisect5: app.py is a NO-OP module. streamlit_app.py does sys.path.insert + import
that module (so the import path runs) and then INLINE-renders the widgets. If this
white-screens, the wedge is triggered by the import-of-submodule act itself (not the
widgets). If it does NOT white-screen, the wedge is in running app.py's top-level
code via the submodule reload path.
"""
import pathlib
import sys

sys.path.insert(0, str(pathlib.Path(__file__).parent / "src"))

import job_agent.ui.app  # noqa: E402,F401  -- exercises the submodule load path

import streamlit as st

st.set_page_config(page_title="EU Job Agent", layout="wide")
st.caption("build bisect5")

languages_raw = st.sidebar.text_input("Languages (ISO-639-1, comma)", value="en, fr")
st.write(f"len = {len(languages_raw)}")