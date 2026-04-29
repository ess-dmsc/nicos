description = "High-level interface to the Selene Guide 2 components"

includes = ["sg2-measurement-cart", "sg2-screwdriver", "sg2-interferometer"]

display_order = 40  # sort before default devices

devices = dict(
    sr2=device(
        "nicos_ess.estia.devices.selene.SeleneRobot",
        description="Selene 2 Robot",
        position_data="/ess/ecdc/nicos-core/nicos_ess/estia/devices/selene2_data.yml",
        engaged1=0.00,
        retracted1=-29.00,
        engaged2=0.00,
        retracted2=-28.00,
        delta12=358.7,
        move_x="sg2_robot_pos",
        move_z="sg2_robot_vert",
        adjust1="sg2_screwdriver_adjust_2",
        approach1="sg2_screwdriver_approach_2",
        hex_state1="sg2_screwdriver_hex_state_2",
        adjust2="sg2_screwdriver_adjust_1",
        approach2="sg2_screwdriver_approach_1",
        hex_state2="sg2_screwdriver_hex_state_1",
        vertical_screws=(3, 5, 6),
        unit="Item/Group",
    ),
    sm2=device(
        "nicos_ess.estia.devices.selene.SeleneMetrology",
        description="Selene 2 Metrology",
        unit="Item/Group",
        m_cart="mcart2",
        interferometer="multiline2",
        cart_center=3453.0,
        ch_u_h1="ch23",
        ch_u_h2="ch24",
        ch_d_h1="ch19",
        ch_d_h2="ch20",
        ch_u_v1="ch21",
        ch_u_v2="ch22",
        ch_d_v1="ch17",
        ch_d_v2="ch18",
    ),
)
