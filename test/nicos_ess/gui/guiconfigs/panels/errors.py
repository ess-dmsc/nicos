"""Minimal ESS guiconfig for ErrorPanel startup tests."""

main_window = panel("nicos_ess.gui.panels.errors.ErrorPanel")
windows = []
tools = []
options = {
    "facility": "ess",
    "mainwindow_class": "nicos_ess.gui.mainwindow.MainWindow",
}
