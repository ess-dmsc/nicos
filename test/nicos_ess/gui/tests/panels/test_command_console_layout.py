"""Layout startup tests for shared ESS GUI panel wiring."""

from __future__ import annotations


guiconfig_name = "layouts/command_console.py"
panel_name = "Command"


def test_command_panel_discovers_console_in_shared_layout(gui_window, gui_panel):
    """postInit wiring should find the real ConsolePanel in the same window."""
    console_panel = gui_window.getPanel("Console")

    assert console_panel is not None
    assert gui_panel.console is console_panel
    assert gui_panel.inputFrame.isEnabled() is True
