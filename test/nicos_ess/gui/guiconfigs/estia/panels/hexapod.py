"""Minimal ESS guiconfig for ESTIA HexapodPanel startup tests."""

main_window = panel("nicos_ess.estia.gui.panels.hexapod.HexapodPanel")
windows = []
tools = []
options = {
    "facility": "ess",
    "mainwindow_class": "nicos_ess.gui.mainwindow.MainWindow",
}
