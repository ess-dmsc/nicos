"""Minimal ESS guiconfig for live_pyqt.LiveDataPanel startup tests."""

main_window = panel("nicos_ess.gui.panels.live_pyqt.LiveDataPanel")
windows = []
tools = []
options = {
    "facility": "ess",
    "mainwindow_class": "nicos_ess.gui.mainwindow.MainWindow",
}
