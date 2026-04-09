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
                            "Live Data Panel",
                            panel("nicos_ess.gui.panels.livedata.LiveDataPanel"),
                        ),
                        (
                            "Detector Image",
                            panel("nicos_ess.gui.panels.live_pyqt.MultiLiveDataPanel"),
                        ),
                        (
                            "Hexapod",
                            panel(
                                "nicos_ess.estia.gui.panels.hexapod.HexapodPanel",
                                devname="estia_hexapod",
                            ),
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
                    cart_position="meas_cart_position1",
                    offsetx=0,
                ),
                robot_options=dict(
                    title="Robot Selene 1 (view inverted)",
                    posx="sg1_robot_pos",
                    posz="sg1_robot_vert",
                    approach1="sg1_screwdriver_approach_1",
                    rotation1="sg1_screwdriver_adjust_1",
                    approach2="sg1_screwdriver_approach_2",
                    rotation2="sg1_screwdriver_adjust_2",
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
                    cart_position="meas_cart_position2",
                    offsetx=0,
                ),
                robot_options=dict(
                    title="Robot Selene 2",
                    selene=2,
                    posx="sg2_robot_pos",
                    posz="sg2_robot_vert",
                    approach1="sg2_screwdriver_approach_2",
                    rotation1="sg2_screwdriver_adjust_2",
                    approach2="sg2_screwdriver_approach_1",
                    rotation2="sg2_screwdriver_adjust_1",
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
