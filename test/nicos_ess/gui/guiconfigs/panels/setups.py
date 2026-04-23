"""Minimal ESS guiconfig for SetupsPanel startup tests."""

main_window = panel("nicos_ess.gui.panels.setups.SetupsPanel")
windows = []
tools = []
options = {
    "facility": "ess",
    "mainwindow_class": "nicos_ess.gui.mainwindow.MainWindow",
}
