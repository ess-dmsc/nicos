"""Minimal ESS guiconfig for TBL MultiLiveDataPanel startup tests."""

main_window = panel("nicos_ess.tbl.gui.panels.live.MultiLiveDataPanel")
windows = []
tools = []
options = {
    "facility": "ess",
    "mainwindow_class": "nicos_ess.gui.mainwindow.MainWindow",
}
