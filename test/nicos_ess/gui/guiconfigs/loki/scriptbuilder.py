"""Minimal ESS guiconfig for LokiScriptBuilderPanel startup tests."""

main_window = panel("nicos_ess.loki.gui.scriptbuilder.LokiScriptBuilderPanel")
windows = []
tools = []
options = {
    "facility": "ess",
    "mainwindow_class": "nicos_ess.gui.mainwindow.MainWindow",
}
