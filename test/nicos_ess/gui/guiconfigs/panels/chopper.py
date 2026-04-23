"""Minimal ESS guiconfig for ChopperPanel startup tests."""

main_window = panel("nicos_ess.gui.panels.chopper.ChopperPanel")
windows = []
tools = []
options = {
    "facility": "ess",
    "mainwindow_class": "nicos_ess.gui.mainwindow.MainWindow",
}
