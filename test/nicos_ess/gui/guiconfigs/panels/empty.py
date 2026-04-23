"""Minimal ESS guiconfig for EmptyPanel startup tests."""

main_window = panel("nicos_ess.gui.panels.empty.EmptyPanel")
windows = []
tools = []
options = {
    "facility": "ess",
    "mainwindow_class": "nicos_ess.gui.mainwindow.MainWindow",
}
