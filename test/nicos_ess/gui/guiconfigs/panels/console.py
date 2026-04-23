"""Dedicated ESS ConsolePanel guiconfig for panel-focused tests."""

main_window = panel("nicos_ess.gui.panels.console.ConsolePanel")
windows = []
tools = []
options = {
    "facility": "ess",
    "mainwindow_class": "nicos_ess.gui.mainwindow.MainWindow",
}
