# ruff: noqa: F821
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
                            panel(
                                "nicos_ess.gui.panels.chopper.ChopperPanel",
                                guide_pos="DOWN",
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
                ),  # vsplit
                panel(
                    "nicos_ess.gui.panels.devices.DevicesPanel",
                    dockpos="right",
                    show_target=True,
                ),
            ),  # hsplit
        ),
        (
            "Scripting",
            panel("nicos_ess.gui.panels.editor.EditorPanel", tools=None),
        ),
        (
            "Selene 1",
            panel(
                "nicos_ess.estia.gui.panels.selene.SelenePanel",
                metrology_options=dict(
                    title="Metrology Selene 1",
                    positions=["ch27", "ch28"],
                    selene=1,
                    cart_position="mpos",
                    offsetx=0,
                ),
                robot_options=dict(
                    title="Robot Selene 1 (view inverted)",
                    posx="robot_pos",
                    posz="robot_vert",
                    approach1="driver1_1_approach",
                    rotation1="driver1_1_adjust",
                    approach2="driver1_2_approach",
                    rotation2="driver1_2_adjust",
                    robot="sr1",
                    offsetx=165.0,
                    offsetz=65.0,
                    deckpos="right",
                ),
            ),
        ),
        (
            "Selene 2",
            panel(
                "nicos_ess.estia.gui.panels.selene.SelenePanel",
                metrology_options=dict(
                    title="Metrology Selene 2 (view inverted)",
                    positions=["ch27", "ch28"],
                    selene=2,
                    cart_position="mpos2",
                    offsetx=0,
                ),
                robot_options=dict(
                    title="Robot Selene 2",
                    selene=2,
                    posx="robot2_pos",
                    posz="robot2_vert",
                    approach1="driver2_2_approach",
                    rotation1="driver2_2_adjust",
                    approach2="driver2_1_approach",
                    rotation2="driver2_1_adjust",
                    robot="sr2",
                    offsetx=-40.0,
                    offsetz=65.0,
                    deckpos="right",
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
        margins=(0, 0, 0, 0),
        textpadding=(30, 20),
    ),  # tabbed
)  # docked

windows = []

options = {
    "facility": "ess",
    "mainwindow_class": "nicos_ess.gui.mainwindow.MainWindow",
}
