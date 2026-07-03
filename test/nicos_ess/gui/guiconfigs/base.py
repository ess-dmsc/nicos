"""Base ESS GUI test shell with no special panel dependencies."""

main_window = panel("nicos_ess.gui.panels.empty.EmptyPanel")
windows = []
tools = []
options = {
    "facility": "ess",
    "mainwindow_class": "nicos_ess.gui.mainwindow.MainWindow",
}
