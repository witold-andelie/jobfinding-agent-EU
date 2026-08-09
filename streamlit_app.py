"""Minimal repro: ONLY a sidebar text_input. No imports of job_agent, no secrets, no
session_state, no widgets beyond one text_input. If deleting a char in this still
white-screens on Cloud, the bug is in the Streamlit Cloud platform layer (not our
code); if it does NOT white-screen, we add things back one by one to bisect.
"""
import streamlit as st

st.set_page_config(page_title="Minimal Repro", layout="wide")
st.title("Minimal Repro")
v = st.sidebar.text_input("Languages (ISO-639-1, comma)", value="en, fr")
st.write(f"You typed: {v!r}")
st.write(f"len={len(v)}")