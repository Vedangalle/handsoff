"""Headless Streamlit application smoke and interaction tests."""

from __future__ import annotations

from pathlib import Path

from streamlit.testing.v1 import AppTest

ROOT = Path(__file__).resolve().parents[2]
APP = ROOT / "streamlit_app.py"
SELECTBOX_COUNT = 2
METRIC_COUNT = 4
TAB_COUNT = 7
MINIMUM_DATAFRAME_COUNT = 7
APP_TIMEOUT_SECONDS = 30


def test_streamlit_app_starts_without_providers_and_runs_scenario() -> None:
    """The public entrypoint is complete with no secrets or network access."""
    app = AppTest.from_file(APP, default_timeout=APP_TIMEOUT_SECONDS).run()
    assert not app.exception
    assert app.title[0].value == "Handsoff"
    assert len(app.selectbox) == SELECTBOX_COUNT
    assert len(app.info) == 1

    app.button[0].click().run()
    assert not app.exception
    assert len(app.success) == 1
    assert len(app.metric) == METRIC_COUNT
    assert len(app.tabs) == TAB_COUNT
    assert len(app.dataframe) >= MINIMUM_DATAFRAME_COUNT

    app.button[1].click().run()
    assert not app.exception
    assert len(app.success) == 0
    assert len(app.info) == 1


def test_streamlit_apptest_sessions_do_not_share_results() -> None:
    """Independent browser simulations do not share mutable result state."""
    first = AppTest.from_file(APP, default_timeout=APP_TIMEOUT_SECONDS).run()
    second = AppTest.from_file(APP, default_timeout=APP_TIMEOUT_SECONDS).run()
    first.button[0].click().run()
    assert len(first.success) == 1
    assert len(second.success) == 0
