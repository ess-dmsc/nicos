"""Minimal ESS guiconfig for DREAM ComparisonPanel startup tests."""

main_window = panel("nicos_ess.dream.gui.comparison_panel.ComparisonPanel")
windows = []
tools = []
options = {
    "facility": "ess",
    "mainwindow_class": "nicos_ess.gui.mainwindow.MainWindow",
}
