"""Boot the Streamlit app via AppTest and assert it renders without exceptions.

Skipped automatically when streamlit isn't installed (it's an optional `ui` extra).
"""

from pathlib import Path

import pytest

pytest.importorskip("streamlit")

from streamlit.testing.v1 import AppTest


def _click_find(at):
    """Matches are computed on demand — click 'Find / refresh jobs' (Demo data, offline)."""
    find = [b for b in at.button if b.label and "Find" in b.label]
    assert find, "expected a 'Find / refresh jobs' button"
    return find[0].click().run()


def test_app_boots_and_shows_matches() -> None:
    app = Path(__file__).parents[2] / "src" / "job_agent" / "ui" / "app.py"
    at = AppTest.from_file(app, default_timeout=30).run()
    assert not at.exception
    assert any("EU Job Agent" in t.value for t in at.title)
    _click_find(at)
    assert not at.exception
    assert len(at.expander) >= 1  # job cards rendered after the search


def test_tracking_an_application_flows_to_applications_tab() -> None:
    app = Path(__file__).parents[2] / "src" / "job_agent" / "ui" / "app.py"
    at = AppTest.from_file(app, default_timeout=30).run()
    _click_find(at)
    track_buttons = [b for b in at.button if b.key and b.key.startswith("tr-")]
    assert track_buttons, "expected a 'Track application' button"
    track_buttons[0].click().run()
    assert not at.exception  # creating + storing an application did not error
