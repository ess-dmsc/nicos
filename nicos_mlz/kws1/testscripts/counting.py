# pylint: skip-file

# test: subdirs = kws1
# test: setups = kws1, waterjulabo
# test: setupcode = FinishExperiment()
# test: setupcode = NewExperiment('0')
# test: skip

ClearSamples()
SetSample(
    1,
    "Alu1",
    aperture=(1.2, 5.4, 7.0, 7.0),
    position={"sam_trans_x": 208.0, "sam_trans_y": 202.5},
    timefactor=1.0,
    thickness=1.0,
    detoffset=-315.0,
    comment="",
)
SetSample(
    2,
    "Alu2",
    aperture=(1.2, 5.4, 7.0, 7.0),
    position={"sam_trans_x": 235.0, "sam_trans_y": 202.5},
    timefactor=1.0,
    thickness=1.0,
    detoffset=-315.0,
    comment="",
)
SetSample(
    3,
    "Alu3",
    aperture=(1.2, 5.4, 7.0, 7.0),
    position={"sam_trans_x": 262.0, "sam_trans_y": 202.5},
    timefactor=1.0,
    thickness=1.0,
    detoffset=-315.0,
    comment="",
)
SetSample(
    4,
    "Alu10",
    aperture=(1.2, 5.4, 7.0, 7.0),
    position={"sam_trans_x": 289.0, "sam_trans_y": 202.5},
    timefactor=1.0,
    thickness=1.0,
    detoffset=-315.0,
    comment="",
)
SetSample(
    5,
    "Alu11",
    aperture=(1.2, 5.4, 12.0, 12.0),
    position={"sam_trans_x": 316.0, "sam_trans_y": 202.5},
    timefactor=1.0,
    thickness=1.0,
    detoffset=-315.0,
    comment="",
)
SetSample(
    6,
    "Alu19",
    aperture=(1.2, 5.4, 15.0, 15.0),
    position={"sam_trans_x": 343.0, "sam_trans_y": 202.5},
    timefactor=1.0,
    thickness=1.0,
    detoffset=-315.0,
    comment="",
)

SetupNormal()
notify("new test script started")
kwscount(
    sample="Alu1",
    selector="7A",
    detector="20m",
    chopper="10.0%",
    collimation="20m (30x30)",
    polarizer="up",
    time=720.0,
    T_julabo=25.0,
)
kwscount(
    sample="Alu2",
    selector="7A",
    detector="20m",
    chopper="10.0%",
    collimation="20m (30x30)",
    polarizer="up",
    time=720.0,
    T_julabo=25.0,
)
kwscount(
    sample="Alu3",
    selector="7A",
    detector="20m",
    chopper="10.0%",
    collimation="20m (30x30)",
    polarizer="up",
    time=720.0,
    T_julabo=25.0,
)
kwscount(
    sample="Alu10",
    selector="7A",
    detector="20m",
    chopper="10.0%",
    collimation="20m (30x30)",
    polarizer="up",
    time=720.0,
    T_julabo=25.0,
)
kwscount(
    sample="Alu11",
    selector="7A",
    detector="20m",
    chopper="10.0%",
    collimation="20m (30x30)",
    polarizer="up",
    time=720.0,
    T_julabo=25.0,
)
kwscount(
    sample="Alu19",
    selector="7A",
    detector="20m",
    chopper="10.0%",
    collimation="20m (30x30)",
    polarizer="up",
    time=720.0,
    T_julabo=25.0,
)
notify("7A, 20m, 10.0%, finished")
kwscount(
    sample="Alu1",
    selector="6A",
    detector="20m",
    chopper="off",
    collimation="20m (30x30)",
    polarizer="down",
    time=720.0,
    T_julabo=20.0,
)
kwscount(
    sample="Alu2",
    selector="6A",
    detector="20m",
    chopper="off",
    collimation="20m (30x30)",
    polarizer="down",
    time=720.0,
    T_julabo=20.0,
)
kwscount(
    sample="Alu3",
    selector="6A",
    detector="20m",
    chopper="off",
    collimation="20m (30x30)",
    polarizer="down",
    time=720.0,
    T_julabo=20.0,
)
kwscount(
    sample="Alu10",
    selector="6A",
    detector="20m",
    chopper="off",
    collimation="20m (30x30)",
    polarizer="down",
    time=720.0,
    T_julabo=20.0,
)
kwscount(
    sample="Alu11",
    selector="6A",
    detector="20m",
    chopper="off",
    collimation="20m (30x30)",
    polarizer="down",
    time=720.0,
    T_julabo=20.0,
)
kwscount(
    sample="Alu19",
    selector="6A",
    detector="20m",
    chopper="off",
    collimation="20m (30x30)",
    polarizer="down",
    time=720.0,
    T_julabo=20.0,
)
notify("6A, 20m, chopper off, finished")
kwscount(
    sample="Alu1",
    selector="5A",
    detector="8m",
    chopper="2.5%",
    collimation="8m (30x30)",
    polarizer="up",
    time=720.0,
    T_julabo=30.0,
)
kwscount(
    sample="Alu2",
    selector="5A",
    detector="8m",
    chopper="2.5%",
    collimation="8m (30x30)",
    polarizer="up",
    time=720.0,
    T_julabo=30.0,
)
kwscount(
    sample="Alu3",
    selector="5A",
    detector="8m",
    chopper="2.5%",
    collimation="8m (30x30)",
    polarizer="up",
    time=720.0,
    T_julabo=30.0,
)
kwscount(
    sample="Alu10",
    selector="5A",
    detector="8m",
    chopper="2.5%",
    collimation="8m (30x30)",
    polarizer="up",
    time=720.0,
    T_julabo=30.0,
)
kwscount(
    sample="Alu11",
    selector="5A",
    detector="8m",
    chopper="2.5%",
    collimation="8m (30x30)",
    polarizer="up",
    time=720.0,
    T_julabo=30.0,
)
kwscount(
    sample="Alu19",
    selector="5A",
    detector="8m",
    chopper="2.5%",
    collimation="8m (30x30)",
    polarizer="up",
    time=720.0,
    T_julabo=30.0,
)
notify("5A, 8m, 2.5%, finished")
kwscount(
    sample="Alu1",
    selector="10A",
    detector="8m",
    chopper="off",
    collimation="14m (30x30)",
    polarizer="out",
    time=720.0,
    T_julabo=20.0,
)
kwscount(
    sample="Alu2",
    selector="10A",
    detector="8m",
    chopper="off",
    collimation="14m (30x30)",
    polarizer="out",
    time=720.0,
    T_julabo=20.0,
)
kwscount(
    sample="Alu3",
    selector="10A",
    detector="8m",
    chopper="off",
    collimation="14m (30x30)",
    polarizer="out",
    time=720.0,
    T_julabo=20.0,
)
kwscount(
    sample="Alu10",
    selector="10A",
    detector="8m",
    chopper="off",
    collimation="14m (30x30)",
    polarizer="out",
    time=720.0,
    T_julabo=20.0,
)
kwscount(
    sample="Alu11",
    selector="10A",
    detector="8m",
    chopper="off",
    collimation="14m (30x30)",
    polarizer="out",
    time=720.0,
    T_julabo=20.0,
)
kwscount(
    sample="Alu19",
    selector="10A",
    detector="8m",
    chopper="off",
    collimation="14m (30x30)",
    polarizer="out",
    time=720.0,
    T_julabo=20.0,
)
notify("10A, 8m, chopper off, finished")
