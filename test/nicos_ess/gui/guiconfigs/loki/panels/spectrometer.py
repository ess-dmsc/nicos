"""Minimal ESS guiconfig for LoKI SpectrometerPanel startup tests."""

main_window = panel("nicos_ess.loki.gui.panels.spectrometer.SpectrometerPanel")
windows = []
tools = []
options = {
    "facility": "ess",
    "mainwindow_class": "nicos_ess.gui.mainwindow.MainWindow",
}
