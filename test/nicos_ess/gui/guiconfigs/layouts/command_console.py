"""Small multi-panel layout used to smoke-test shared panel wiring."""

main_window = vbox(
    panel("nicos_ess.gui.panels.cmdbuilder.CommandPanel"),
    panel("nicos_ess.gui.panels.console.ConsolePanel"),
)
windows = []
tools = []
options = {
    "facility": "ess",
    "mainwindow_class": "nicos_ess.gui.mainwindow.MainWindow",
}
