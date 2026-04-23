"""Startup coverage for LoKI GUI modules outside ``panels/``."""

from __future__ import annotations

import pytest

from test.nicos_ess.gui.helpers import (
    assert_panel_starts_clean,
    assert_panel_survives_lifecycle_events_cleanly,
    panel_case,
)


_LOKI_CASES = [
    panel_case(
        "sample-holder-config",
        "nicos_ess.loki.gui.sample_holder_config.LokiSampleHolderPanel",
    ),
    panel_case("scriptbuilder", "nicos_ess.loki.gui.scriptbuilder.LokiScriptBuilderPanel"),
]


@pytest.mark.parametrize(
    ("guiconfig_name", "guiconfig_text", "panel_class", "seed_daemon"),
    _LOKI_CASES,
)
def test_panel_starts_without_warnings_or_errors(
    gui_window_factory,
    gui_window_from_name,
    fake_daemon,
    caplog,
    qtbot,
    guiconfig_name,
    guiconfig_text,
    panel_class,
    seed_daemon,
):
    assert_panel_starts_clean(
        gui_window_factory=gui_window_factory,
        gui_window_from_name=gui_window_from_name,
        fake_daemon=fake_daemon,
        caplog=caplog,
        qtbot=qtbot,
        guiconfig_name=guiconfig_name,
        guiconfig_text=guiconfig_text,
        panel_class=panel_class,
        seed_daemon=seed_daemon,
    )


@pytest.mark.parametrize(
    ("guiconfig_name", "guiconfig_text", "panel_class", "seed_daemon"),
    _LOKI_CASES,
)
def test_panel_survives_normal_lifecycle_events_without_warnings_or_errors(
    gui_window_factory,
    gui_window_from_name,
    fake_daemon,
    caplog,
    qtbot,
    guiconfig_name,
    guiconfig_text,
    panel_class,
    seed_daemon,
):
    assert_panel_survives_lifecycle_events_cleanly(
        gui_window_factory=gui_window_factory,
        gui_window_from_name=gui_window_from_name,
        fake_daemon=fake_daemon,
        caplog=caplog,
        qtbot=qtbot,
        guiconfig_name=guiconfig_name,
        guiconfig_text=guiconfig_text,
        panel_class=panel_class,
        seed_daemon=seed_daemon,
    )
