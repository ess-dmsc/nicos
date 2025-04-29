expcolumn = Column(
    Block(
        "Experiment",  # block name
        [  # a list of rows in that block
            BlockRow(
                Field(name="Proposal", key="exp/proposal", width=7),
                Field(name="Title", key="exp/title", width=20, istext=True, maxlen=20),
                Field(name="Current status", key="exp/action", width=30, istext=True),
                Field(name="Last file", key="exp/lastpoint"),
            ),
        ],
        # This block will always be displayed
    ),
)


devcolumn = Column(
    Block(
        "YMIR motion cabinet 1:",
        [
            BlockRow(Field(dev="heavy_shutter_status", name="Heavy shutter")),
        ],
        # setup that must be loaded for this block to be shown
        setups="motion_cabinet_1",
    ),
    Block(
        "Chopper",
        [
            BlockRow(
                Field(dev="mini_chopper_speed", name="Speed"),
                Field(dev="mini_chopper_alarm_level", name="Alarms"),
            ),
        ],
        # setup 'detector' must and 'qmesydaq' must __not__ be loaded to
        # show this block
        setups="choppers",
    ),
    # Block(
    #     "Triple-axis",
    #     [
    #         BlockRow(
    #             Field(dev="tas[0]", name="H", format="%.3f", unit=" "),
    #             Field(dev="tas[1]", name="K", format="%.3f", unit=" "),
    #             Field(dev="tas[2]", name="L", format="%.3f", unit=" "),
    #             Field(dev="tas[3]", name="E", format="%.3f", unit=" "),
    #         ),
    #         BlockRow(
    #             Field(key="tas/scanmode", name="Mode"),
    #             Field(dev="mono", name="ki"),
    #             Field(dev="ana", name="kf"),
    #             Field(key="tas/energytransferunit", name="Unit"),
    #         ),
    #     ],
    #     setups="tas",
    # ),
)

devices = dict(
    Monitor=device(
        "nicos.services.monitor.qt.Monitor",
        title="My status monitor",
        cache="localhost:14869",
        layout=[Row(expcolumn), Row(devcolumn)],
    ),
)
