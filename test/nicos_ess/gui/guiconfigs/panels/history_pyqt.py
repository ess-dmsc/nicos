"""Minimal ESS guiconfig for history_pyqt.HistoryPanel startup tests."""

main_window = panel("nicos_ess.gui.panels.history_pyqt.HistoryPanel")
windows = []
tools = []
options = {
    "facility": "ess",
    "mainwindow_class": "nicos_ess.gui.mainwindow.MainWindow",
}
