"""Minimal ESS guiconfig for ODIN MultiLiveDataPanel startup tests."""

main_window = panel("nicos_ess.odin.gui.panels.live.MultiLiveDataPanel")
windows = []
tools = []
options = {
    "facility": "ess",
    "mainwindow_class": "nicos_ess.gui.mainwindow.MainWindow",
}
