"""Minimal NICOS guiconfig for the ESS DevicesPanel test harness."""

main_window = panel("nicos_ess.gui.panels.devices.DevicesPanel")
windows = []
tools = []
options = {
    "facility": "ess",
    "mainwindow_class": "nicos_ess.gui.mainwindow.MainWindow",
}
