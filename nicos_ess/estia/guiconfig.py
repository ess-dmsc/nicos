"""NICOS GUI default configuration."""

main_window = docked(
    tabbed(
        ("Experiment", panel("nicos_ess.gui.panels.exp_panel.ExpPanel")),
        ("Setup", panel("nicos.clients.flowui.panels.setup_panel.SetupsPanel")),
        ("  ", panel("nicos.clients.flowui.panels.empty.EmptyPanel")),
        (
            "Instrument interaction",
            hsplit(
                vbox(
                    panel(
                        "nicos.clients.flowui.panels.cmdbuilder.CommandPanel",
                        modules=["nicos.clients.gui.cmdlets"],
                    ),
                    vsplit(
                        tabbed(
                            (
                                "Output",
                                panel(
                                    "nicos.clients.flowui.panels.console.ConsolePanel",
                                    hasinput=False,
                                ),
                            ),
                            (
                                "Scan Plot",
                                panel("nicos.clients.flowui.panels.scans.ScansPanel"),
                            ),
                            (
                                "Detector Image",
                                panel(
                                    "nicos.clients.flowui.panels.live.MultiLiveDataPanel"
                                ),
                            ),
                            (
                                "Script Status",
                                panel(
                                    "nicos.clients.flowui.panels.status.ScriptStatusPanel",
                                    eta=True,
                                ),
                            ),
                        ),
                    ),
                ),  # vbox
                panel(
                    "nicos.clients.flowui.panels.devices.DevicesPanel",
                    dockpos="right",
                    param_display={"Exp": ["lastpoint", "lastscan"]},
                    filters=[],
                ),
            ),  # hsplit
        ),
        (
            "Scripting",
            panel("nicos.clients.flowui.panels.editor.EditorPanel", tools=None),
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
                    channels=[
                        # (CHi, pos, diagonal)
                        ("ch21", (-45, 80), False),
                        ("ch22", (-45, 35), False),
                        ("ch23", (-46, -144), True),
                        ("ch24", (-46, -202), True),
                        ("ch17", (45, 80), False),
                        ("ch18", (45, 35), False),
                        ("ch19", (46, -144), True),
                        ("ch20", (46, -202), True),
                    ],
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
                    screw_group=[
                        # relative location of screws in each mirror group
                        # (x, z, active, item-1)
                        (50, 234, True, 3),
                        (50, 64, True, 4),
                        (50, 30, True, 5),
                        (445, 234, True, 0),
                        (445, 128, True, 1),
                        (445, 64, True, 2),
                        # second guide, not active
                        (50, 500 - 128, False, -2),
                        (50, 500 - 64, False, -2),
                        (50, 500 - 30, False, -2),
                        (445, 500 - 234, False, -2),
                        (445, 500 - 128, False, -2),
                        (445, 500 - 64, False, -2),
                    ],
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
                    channels=[
                        # (CHi, pos, diagonal)
                        ("ch21", (-45, 80), False),
                        ("ch22", (-45, 35), False),
                        ("ch23", (-46, -144), True),
                        ("ch24", (-46, -202), True),
                        ("ch17", (45, 80), False),
                        ("ch18", (45, 35), False),
                        ("ch19", (46, -144), True),
                        ("ch20", (46, -202), True),
                    ],
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
                    screw_group=[
                        # relative location of screws in each mirror group
                        # (x, z, active, item-1)
                        (50, 234, False, -2),
                        (50, 128, False, -2),
                        (50, 64, False, -2),
                        (445, 128, False, -2),
                        (445, 64, False, -2),
                        (445, 30, False, -2),
                        # second guide, active
                        (50, 500 - 234, True, 5),
                        (50, 500 - 128, True, 4),
                        (50, 500 - 64, True, 3),
                        (445, 500 - 128, True, 2),
                        (445, 500 - 64, True, 1),
                        (445, 500 - 30, True, 0),
                    ],
                ),
            ),
        ),
        (
            "History",
            panel("nicos.clients.flowui.panels.history.HistoryPanel"),
        ),
        (
            "Logs",
            tabbed(
                ("Errors", panel("nicos.clients.gui.panels.errors.ErrorPanel")),
                (
                    "Log files",
                    panel("nicos.clients.gui.panels.logviewer.LogViewerPanel"),
                ),
            ),
        ),
        position="left",
        margins=(0, 0, 0, 0),
        textpadding=(30, 20),
    ),  # tabbed
)  # docked

windows = []

tools = [
    tool(
        "Report NICOS bug or request enhancement",
        "nicos.clients.gui.tools.bugreport.BugreportTool",
    ),
]

options = {
    "facility": "ess",
    "mainwindow_class": "nicos.clients.flowui.mainwindow.MainWindow",
}
