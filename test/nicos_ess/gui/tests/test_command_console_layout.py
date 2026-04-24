"""Layout startup tests for shared ESS GUI panel wiring."""

from __future__ import annotations

from test.nicos_ess.gui.helpers import get_panel_by_class


guiconfig_name = "command_console.py"
panel_class = "nicos_ess.gui.panels.cmdbuilder.CommandPanel"


def test_command_panel_discovers_console_in_shared_layout(gui_window, gui_panel):
    """postInit wiring should find the real ConsolePanel in the same window."""
    console_panel = get_panel_by_class(gui_window, "nicos_ess.gui.panels.console.ConsolePanel")

    assert console_panel is not None
    assert gui_panel.console is console_panel
    assert gui_panel.inputFrame.isEnabled() is True
