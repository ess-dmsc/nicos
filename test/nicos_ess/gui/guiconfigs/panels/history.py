"""Minimal ESS guiconfig for HistoryPanel startup tests."""

main_window = panel("nicos_ess.gui.panels.history.HistoryPanel")
windows = []
tools = []
options = {
    "facility": "ess",
    "mainwindow_class": "nicos_ess.gui.mainwindow.MainWindow",
}
