description = "Chopper [Monitor 01]"
group = "special"

# Legend for _chconfigcol
# dev = '...' represents here only the possible values, no devices

# Legend for the chopper discs
# speed  = Revolutions per minute
# angle  = Angle
# phase  = Disk Phases
# gear   = Speed Factor
# status = Error Status

_chhealth = Column(
    Block(
        "Basic",
        [
            BlockRow(
                Field(name="Fatal", key="chopper/fatal", width=10),
            ),
            BlockRow(
                Field(name="noWARNUNG", dev="chopper_no_Warning", width=7),
            ),
        ],
    ),
)

_chconfigcol = Column(
    # This block contains the parameters set through chopper_config
    Block(
        " Chopper Configuration ",
        [
            BlockRow(
                Field(
                    name="\u03bb\u2098\u1d62\u2099",
                    key="chopper/wlmin",
                    width=14,
                    format="%.1f",
                    unit="(\u212b)",
                ),
                Field(
                    name="\u03bb\u2098\u2090\u2093",
                    key="chopper/wlmax",
                    width=14,
                    format="%.1f",
                    unit="(\u212b)",
                ),
                # it is not the resolution by itsself. It is the disk 2 position
                # set in chopper_config
                Field(
                    name="disk 2 position",
                    key="chopper/resolution",
                    width=14,
                    unit="(1 - 6)",
                ),
                Field(
                    name="disk 1 - detector distance",
                    key="chopper/dist",
                    width=14,
                    format="%.3f",
                    unit="(m)",
                ),
                Field(name="gap", key="chopper/gap", width=10, format="%.2f"),
            ),
            BlockRow(
                Field(
                    name="angular speed",
                    key="chopper/speed",
                    width=10,
                    format="%.1f",
                    unit="(rpm)",
                ),
                Field(
                    name="disk 2 phase",
                    key="chopper2/phase",
                    width=10,
                    format="%.2f",
                    unit="(deg)",
                ),
                Field(
                    name="disk 3 phase",
                    key="chopper3/phase",
                    width=10,
                    format="%.2f",
                    unit="(deg)",
                ),
                Field(
                    name="disk 4 phase",
                    key="chopper4/phase",
                    width=10,
                    format="%.2f",
                    unit="(deg)",
                ),
                Field(
                    name="disk 5 phase",
                    key="chopper5/phase",
                    width=10,
                    format="%.2f",
                    unit="(deg)",
                ),
                Field(
                    name="disk 6 phase",
                    key="chopper6/phase",
                    width=10,
                    format="%.2f",
                    unit="(deg)",
                ),
            ),
        ],
    ),
    # This block contains the actual parameters set for the chopper system
    Block(
        " Chopper Settings ",
        [
            BlockRow(
                Field(name="disk 2 mode", key="chopper/mode", width=20),
                Field(
                    name="disk 2 position", dev="chopper2_pos", width=10, unit="(1 - 5)"
                ),
                # it is not the flight path. I don't know why somebody called it
                # real_flight_path
                Field(
                    name="disc1 - detector distance",
                    dev="real_flight_path",
                    width=14,
                    format="%.3f",
                    unit="(m)",
                ),
                Field(
                    name="resolution \u0394\u03bb/\u03bb ",
                    dev="resolution",
                    width=14,
                    format="%.2f",
                    unit="(%)",
                ),
                Field(
                    name="start delay",
                    key="chopper/delay",
                    width=10,
                    format="%.2f",
                    unit="(deg)",
                ),
            ),
            BlockRow(
                Field(
                    name="angular speed",
                    dev="chopper_speed",
                    width=10,
                    format="%.1f",
                    unit="(rpm)",
                ),
                Field(
                    name="Disk 2 phase",
                    dev="cpt2",
                    width=10,
                    format="%.2f",
                    unit="(deg)",
                ),
                Field(
                    name="Disk 3 phase",
                    dev="cpt3",
                    width=10,
                    format="%.2f",
                    unit="(deg)",
                ),
                Field(
                    name="Disk 4 phase",
                    dev="cpt4",
                    width=10,
                    format="%.2f",
                    unit="(deg)",
                ),
                Field(
                    name="Disk 5 phase",
                    dev="cpt5",
                    width=10,
                    format="%.2f",
                    unit="(deg)",
                ),
                Field(
                    name="Disk 6 phase",
                    dev="cpt6",
                    width=10,
                    format="%.2f",
                    unit="(deg)",
                ),
            ),
        ],
    ),
)

# The time-distance diagram is generated by chopperconfig as a png image and
# should then be displayed. Width and height must be adjusted but they don't
# work in the actual configuration

_tididiagcol = Column(
    Block(
        " Time/Distance Diagram",
        [
            BlockRow(
                Field(
                    widget="nicos_mlz.refsans.gui.monitorwidgets.TimeDistance",
                    chopper1="chopper_speed",
                    disc2_pos="chopper2_pos",
                ),
                # width=30, height=11),
            ),
        ],
    ),
)

# Legend for the chopper discs
# speed  = Revolutions per minute
# angle  = Angle
# phase  = Disk Phases
# gear   = Speed Factor
# status = Error Status


devices = dict(
    Monitor=device(
        "nicos.services.monitor.qt.Monitor",
        showwatchdog=False,
        title=description,
        loglevel="info",
        cache="refsansctrl.refsans.frm2.tum.de",
        prefix="nicos/",
        font="Luxi Sans",
        valuefont="Consolas",
        fontsize=12,
        padding=5,
        layout=[Row(_chconfigcol, _chhealth), Row(_tididiagcol)],
    ),
)
