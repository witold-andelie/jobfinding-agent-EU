"""Boot the Streamlit app via AppTest and assert it renders without exceptions.

Skipped automatically when streamlit isn't installed (it's an optional `ui` extra).
"""

import pytest

pytest.importorskip("streamlit")

from streamlit.testing.v1 import AppTest  # noqa: E402


def test_app_boots_and_shows_matches() -> None:
    at = AppTest.from_file("src/job_agent/ui/app.py", default_timeout=30).run()
    assert not at.exception
    # Title rendered, and the default profile produced a ranked Matches list.
    assert any("EU Job Agent" in t.value for t in at.title)
    assert len(at.expander) >= 1  # at least one job card


def test_tracking_an_application_flows_to_applications_tab() -> None:
    at = AppTest.from_file("src/job_agent/ui/app.py", default_timeout=30).run()
    track_buttons = [b for b in at.button if b.key and b.key.startswith("tr-")]
    assert track_buttons, "expected a 'Track application' button"
    track_buttons[0].click().run()
    assert not at.exception  # creating + storing an application did not error
