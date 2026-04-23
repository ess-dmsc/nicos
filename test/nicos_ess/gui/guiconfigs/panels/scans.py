"""Minimal ESS guiconfig for ScansPanel startup tests."""

main_window = panel("nicos_ess.gui.panels.scans.ScansPanel")
windows = []
tools = []
options = {
    "facility": "ess",
    "mainwindow_class": "nicos_ess.gui.mainwindow.MainWindow",
}
