"""Minimal ESS guiconfig for RheometerPanel startup tests."""

main_window = panel("nicos_ess.gui.panels.rheometer.RheometerPanel")
windows = []
tools = []
options = {
    "facility": "ess",
    "mainwindow_class": "nicos_ess.gui.mainwindow.MainWindow",
}
