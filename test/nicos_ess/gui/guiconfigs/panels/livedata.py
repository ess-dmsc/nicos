"""Minimal ESS guiconfig for livedata.LiveDataPanel startup tests."""

main_window = panel("nicos_ess.gui.panels.livedata.LiveDataPanel")
windows = []
tools = []
options = {
    "facility": "ess",
    "mainwindow_class": "nicos_ess.gui.mainwindow.MainWindow",
}
