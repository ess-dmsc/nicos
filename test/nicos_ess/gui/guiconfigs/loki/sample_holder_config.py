"""Minimal ESS guiconfig for LokiSampleHolderPanel startup tests."""

main_window = panel("nicos_ess.loki.gui.sample_holder_config.LokiSampleHolderPanel")
windows = []
tools = []
options = {
    "facility": "ess",
    "mainwindow_class": "nicos_ess.gui.mainwindow.MainWindow",
}
