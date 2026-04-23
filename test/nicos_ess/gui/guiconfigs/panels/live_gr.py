"""Minimal ESS guiconfig for live_gr.LiveDataPanel startup tests."""

main_window = panel("nicos_ess.gui.panels.live_gr.LiveDataPanel")
windows = []
tools = []
options = {
    "facility": "ess",
    "mainwindow_class": "nicos_ess.gui.mainwindow.MainWindow",
}
