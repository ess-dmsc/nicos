"""Minimal ESS guiconfig for ODIN MetrologySystemPanel startup tests."""

main_window = panel("nicos_ess.odin.gui.metrology_system.MetrologySystemPanel")
windows = []
tools = []
options = {
    "facility": "ess",
    "mainwindow_class": "nicos_ess.gui.mainwindow.MainWindow",
}
