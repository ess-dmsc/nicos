"""Minimal ESS guiconfig for CommandPanel startup tests."""

main_window = panel("nicos_ess.gui.panels.cmdbuilder.CommandPanel")
windows = []
tools = []
options = {
    "facility": "ess",
    "mainwindow_class": "nicos_ess.gui.mainwindow.MainWindow",
}
