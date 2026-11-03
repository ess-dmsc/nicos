"""NICOS GUI default configuration."""

main_window = vbox(
    panel("nicos_ess.gui.panels.dashboard.Dashboard"),
    tabbed(
        ("Experiment", panel("nicos_ess.gui.panels.exp_panel.ExpPanel")),
        ("Setup", panel("nicos_ess.gui.panels.setups.SetupsPanel")),
        ("  ", panel("nicos_ess.gui.panels.empty.EmptyPanel")),
        (
            "Instrument interaction",
            hsplit(
                vbox(
                    panel(
                        "nicos_ess.gui.panels.cmdbuilder.CommandPanel",
                    ),
                    tabbed(
                        (
                            "Output",
                            panel(
                                "nicos_ess.gui.panels.console.ConsolePanel",
                                hasinput=False,
                            ),
                        ),
                        ("Scan Plot", panel("nicos_ess.gui.panels.scans.ScansPanel")),
                        (
                            "Detector Image",
                            panel("nicos_ess.gui.panels.live_pyqt.MultiLiveDataPanel"),
                        ),
                        (
                            "Script Status",
                            panel(
                                "nicos_ess.gui.panels.status.ScriptStatusPanel",
                                eta=True,
                            ),
                        ),
                    ),
                ),  # vsplit
                panel(
                    "nicos_ess.gui.panels.devices.DevicesPanel",
                    dockpos="right",
                ),
            ),  # hsplit
        ),
        (
            "Scripting",
            panel("nicos_ess.gui.panels.remote_editor.EditorPanel", tools=None),
        ),
        (
            "History",
            panel("nicos_ess.gui.panels.history.HistoryPanel"),
        ),
        (
<<<<<<< HEAD
<<<<<<< HEAD
=======
            "History(TESTING)",
            panel("nicos_ess.gui.panels.history_pyqt.HistoryPanel"),
        ),
        (
>>>>>>> c4e2498843 (initial demo instrument from YMIR)
=======
>>>>>>> 314408c9bd (remove ymir devices)
            "Logs",
            tabbed(
                ("Errors", panel("nicos_ess.gui.panels.errors.ErrorPanel")),
                ("Log files", panel("nicos_ess.gui.panels.logviewer.LogViewerPanel")),
            ),
        ),
        position="left",
        margins=(25, 10, 25, 35),
        textpadding=(30, 20),
    ),  # tabbed
)  # docked

windows = []

options = {
    "facility": "ess",
    "mainwindow_class": "nicos_ess.gui.mainwindow.MainWindow",
}
