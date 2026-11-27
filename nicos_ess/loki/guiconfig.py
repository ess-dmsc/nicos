main_window = vbox(
    panel("nicos_ess.gui.panels.dashboard.Dashboard"),
    tabbed(
        (
            "Experiment",
            panel("nicos_ess.gui.panels.exp_panel.ExpPanel", hide_sample=True),
        ),
        ("Instrument Setup", panel("nicos_ess.gui.panels.setups.SetupsPanel")),
        (
            "Sample Configuration",
            panel("nicos_ess.loki.gui.sample_holder_config.LokiSampleHolderPanel"),
        ),
        ("  ", panel("nicos_ess.gui.panels.empty.EmptyPanel")),
        (
            "Instrument Interaction",
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
                            "Choppers",
                            panel("nicos_ess.gui.panels.chopper.ChopperPanel"),
                        ),
                        (
                            "Rheometer Setup",
                            panel(
                                "nicos_ess.gui.panels.rheometer.RheometerPanel",
                                rheometer="rheometer",
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
            "Script Builder",
            panel(
                "nicos_ess.loki.gui.scriptbuilder.LokiScriptBuilderPanel", tools=None
            ),
        ),
        (
            "Scripting",
            hsplit(
                tabbed(
                    (
                        "Script",
                        panel(
                            "nicos_ess.gui.panels.remote_editor.EditorPanel", tools=None
                        ),
                    ),
                    (
                        "Script Status",
                        panel(
                            "nicos_ess.gui.panels.status.ScriptStatusPanel",
                            eta=True,
                        ),
                    ),
                ),
                panel(
                    "nicos_ess.gui.panels.devices.DevicesPanel",
                    dockpos="right",
                ),
            ),
        ),
        (
            "History",
            panel("nicos_ess.gui.panels.history.HistoryPanel"),
        ),
        (
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
    "mainwindow_class": "nicos_ess.gui.mainwindow.MainWindow",
}
