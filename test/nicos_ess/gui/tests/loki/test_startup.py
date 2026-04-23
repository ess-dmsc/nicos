"""Startup coverage for LoKI GUI modules outside ``panels/``."""

from __future__ import annotations

import pytest

from test.nicos_ess.gui.helpers import (
    assert_panel_starts_clean,
    assert_panel_survives_lifecycle_events_cleanly,
)


_LOKI_CASES = [
    pytest.param(
        "loki/sample_holder_config.py",
        "nicos_ess.loki.gui.sample_holder_config.LokiSampleHolderPanel",
        id="sample-holder-config",
    ),
    pytest.param(
        "loki/scriptbuilder.py",
        "nicos_ess.loki.gui.scriptbuilder.LokiScriptBuilderPanel",
        id="scriptbuilder",
    ),
]


@pytest.mark.parametrize(("guiconfig_name", "panel_class"), _LOKI_CASES)
def test_panel_starts_without_warnings_or_errors(
    gui_window_from_name,
    fake_daemon,
    caplog,
    qtbot,
    guiconfig_name,
    panel_class,
):
    assert_panel_starts_clean(
        gui_window_from_name=gui_window_from_name,
        fake_daemon=fake_daemon,
        caplog=caplog,
        qtbot=qtbot,
        guiconfig_name=guiconfig_name,
        panel_class=panel_class,
    )


@pytest.mark.parametrize(("guiconfig_name", "panel_class"), _LOKI_CASES)
def test_panel_survives_normal_lifecycle_events_without_warnings_or_errors(
    gui_window_from_name,
    fake_daemon,
    caplog,
    qtbot,
    guiconfig_name,
    panel_class,
):
    assert_panel_survives_lifecycle_events_cleanly(
        gui_window_from_name=gui_window_from_name,
        fake_daemon=fake_daemon,
        caplog=caplog,
        qtbot=qtbot,
        guiconfig_name=guiconfig_name,
        panel_class=panel_class,
    )
