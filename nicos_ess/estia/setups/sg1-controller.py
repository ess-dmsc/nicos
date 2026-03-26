description = "High-level interface to the Selene Guide 1 components"

includes = ["sg1-measurement-cart", "sg1-screwdriver", "sg1-interferometer"]

display_order = 40  # sort before default devices

devices = dict(
    sr1=device(
        "nicos_ess.estia.devices.selene.SeleneRobot",
        description="Selene 1 Robot",
        position_data="/ess/ecdc/nicos-core/nicos_ess/estia/devices/selene1_data.yml",
        engaged=0.02,
        retracted=27.98,
        delta12=358.7,
        move_x="sg1_robot_pos",
        move_z="sg1_robot_vert",
        adjust1="sg1_screwdriver_adjust_1",
        approach1="sg1_screwdriver_approach_1",
        hex_state1="sg1_screwdriver_hex_state_1",
        adjust2="sg1_screwdriver_adjust_2",
        approach2="sg1_screwdriver_approach_2",
        hex_state2="sg1_screwdriver_hex_state_2",
        vertical_screws=(1, 2, 4),
        unit="Item/Group",
    ),
    sm1=device(
        "nicos_ess.estia.devices.selene.SeleneMetrology",
        description="Selene 1 Metrology",
        unit="Item/Group",
        m_cart="mcart1",
        interferometer="multiline1",
        ch_u_h1="ch01",
        ch_u_h2="ch02",
        ch_d_h1="ch03",
        ch_d_h2="ch04",
        ch_u_v1="ch05",
        ch_u_v2="ch06",
        ch_d_v1="ch07",
        ch_d_v2="ch08",
    ),
)
