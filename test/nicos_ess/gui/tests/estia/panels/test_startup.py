"""Startup coverage for ESTIA panels."""

from __future__ import annotations

import pytest

from test.nicos_ess.gui.helpers import assert_panel_starts_clean


_ESTIA_PANEL_CASES = [
    pytest.param(
        "estia/panels/hexapod.py",
        "nicos_ess.estia.gui.panels.hexapod.HexapodPanel",
        id="hexapod",
    ),
    pytest.param(
        "estia/panels/selene.py",
        "nicos_ess.estia.gui.panels.selene.SelenePanel",
        id="selene",
    ),
]


@pytest.mark.parametrize(("guiconfig_name", "panel_class"), _ESTIA_PANEL_CASES)
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
