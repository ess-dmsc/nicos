"""Minimal ESS guiconfig for HexapodPanel startup tests."""

main_window = panel("nicos_ess.gui.panels.hexapod.HexapodPanel")
windows = []
tools = []
options = {
    "facility": "ess",
    "mainwindow_class": "nicos_ess.gui.mainwindow.MainWindow",
}
