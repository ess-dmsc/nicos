"""Minimal ESS guiconfig for ScriptStatusPanel startup tests."""

main_window = panel("nicos_ess.gui.panels.status.ScriptStatusPanel")
windows = []
tools = []
options = {
    "facility": "ess",
    "mainwindow_class": "nicos_ess.gui.mainwindow.MainWindow",
}
