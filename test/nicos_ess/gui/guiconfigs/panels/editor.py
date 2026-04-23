"""Minimal ESS guiconfig for EditorPanel startup tests."""

main_window = panel("nicos_ess.gui.panels.editor.EditorPanel")
windows = []
tools = []
options = {
    "facility": "ess",
    "mainwindow_class": "nicos_ess.gui.mainwindow.MainWindow",
}
