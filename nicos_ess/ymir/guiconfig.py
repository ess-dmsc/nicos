"""NICOS GUI default configuration."""

main_window = docked(
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
                            "X-ray",
                            panel(
                                "nicos_ess.gui.panels.xray.XrayPanel",
                                model="model_r",
                                status="status_r",
                                beam_align="beam_align_r",
                                interlock="interlock_r",
                                xray="xray",
                                voltage="voltage",
                                voltage_r="voltage_r",
                                current="current",
                                current_r="current_r",
                                focus="focus",
                                vacuum="vacuum_r",
                                temperature="temperature_r",
                                align_x="align_x",
                                align_y="align_y",
                                camera="ad_sim_detector",
                                collector="ad_sim_detector_area_detector_collector",
                                source_motor="source_motor",
                                flatpanel_motor="flatpanel_motor",
                            ),
                        ),
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
                            "Live Data Panel",
                            panel("nicos_ess.gui.panels.livedata.LiveDataPanel"),
                        ),
                        (
                            "Chopper",
                            panel("nicos_ess.gui.panels.chopper.ChopperPanel"),
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
            panel("nicos_ess.gui.panels.editor.EditorPanel", tools=None),
        ),
        (
            "History",
            panel("nicos_ess.gui.panels.history.HistoryPanel"),
        ),
        (
            "History(TESTING)",
            panel("nicos_ess.gui.panels.history_pyqt.HistoryPanel"),
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
