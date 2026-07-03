"""Minimal ESS guiconfig for ESTIA SelenePanel startup tests."""

main_window = panel(
    "nicos_ess.estia.gui.panels.selene.SelenePanel",
    metrology_options={
        "positions": ["top", "bottom"],
        "selene": 1,
        "cart_position": "selene_cart",
        "offsetx": 0,
        "title": "Metrology",
    },
    robot_options={
        "posx": "robot_posx",
        "posz": "robot_posz",
        "approach1": "robot_approach1",
        "rotation1": "robot_rotation1",
        "approach2": "robot_approach2",
        "rotation2": "robot_rotation2",
        "selene": 1,
        "robot": "selene_robot",
        "offsetx": 0,
        "offsetz": 0,
        "title": "Robot",
    },
)
windows = []
tools = []
options = {
    "facility": "ess",
    "mainwindow_class": "nicos_ess.gui.mainwindow.MainWindow",
}
