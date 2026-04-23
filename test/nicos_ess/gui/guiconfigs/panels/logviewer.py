"""Minimal ESS guiconfig for LogViewerPanel startup tests."""

main_window = panel("nicos_ess.gui.panels.logviewer.LogViewerPanel")
windows = []
tools = []
options = {
    "facility": "ess",
    "mainwindow_class": "nicos_ess.gui.mainwindow.MainWindow",
}
