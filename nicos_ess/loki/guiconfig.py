main_window = docked(
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
                            panel("nicos_ess.gui.panels.live_gr.MultiLiveDataPanel"),
                        ),
                        (
                            "Choppers",
                            panel("nicos_ess.gui.panels.chopper.ChopperPanel"),
                        ),
                        (
                            "Spectrometer",
                            panel(
                                "nicos_ess.loki.gui.panels.spectrometer.SpectrometerPanel"
                            ),
                        ),
                        (
                            "Rheometer Setup",
                            panel("nicos_ess.gui.panels.rheometer.RheometerPanel"),
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
            "Script Builder",
            panel(
                "nicos_ess.loki.gui.scriptbuilder.LokiScriptBuilderPanel", tools=None
            ),
        ),
        (
            "Scripting",
            panel("nicos_ess.gui.panels.editor.EditorPanel", tools=None),
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
        margins=(0, 0, 0, 0),
        textpadding=(30, 20),
    ),  # tabbed
)  # docked

windows = []

options = {
    "facility": "ess",
    "mainwindow_class": "nicos_ess.gui.mainwindow.MainWindow",
}
