main_window = vbox(
    panel("nicos_ess.gui.panels.dashboard.Dashboard"),
    tabbed(
        (
            "Experiment",
            panel("nicos_ess.gui.panels.exp_panel.ExpPanel", hide_sample=True),
        ),
        ("Instrument Setup", panel("nicos_ess.gui.panels.setups.SetupsPanel")),
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
                            "Live 1",
                            panel(
                                "nicos_ess.gui.panels.liveview.LiveViewPanel", index=1
                            ),
                        ),
                        (
                            "Live 2",
                            panel(
                                "nicos_ess.gui.panels.liveview.LiveViewPanel", index=2
                            ),
                        ),
                        (
                            "Live 3",
                            panel(
                                "nicos_ess.gui.panels.liveview.LiveViewPanel", index=3
                            ),
                        ),
                        (
                            "Choppers",
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
            panel("nicos_ess.gui.panels.remote_editor.EditorPanel", tools=None),
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
