"""Layout startup tests for shared ESS GUI panel wiring."""

from __future__ import annotations

from test.nicos_ess.gui.helpers import get_panel_by_class


def test_command_panel_discovers_console_in_shared_layout(gui_window_factory):
    """postInit wiring should find the real ConsolePanel in the same window."""
    gui_window = gui_window_factory(relative_path="command_console.py")
    command_panel = get_panel_by_class(
        gui_window, "nicos_ess.gui.panels.cmdbuilder.CommandPanel"
    )
    console_panel = get_panel_by_class(
        gui_window, "nicos_ess.gui.panels.console.ConsolePanel"
    )

    assert console_panel is not None
    assert command_panel.console is console_panel
    assert command_panel.inputFrame.isEnabled() is True
