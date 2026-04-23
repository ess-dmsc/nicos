"""Dedicated ESS DevicesPanel guiconfig for panel-focused tests."""

main_window = panel("nicos_ess.gui.panels.devices.DevicesPanel")
windows = []
tools = []
options = {
    "facility": "ess",
    "mainwindow_class": "nicos_ess.gui.mainwindow.MainWindow",
}
