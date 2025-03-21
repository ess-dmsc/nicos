description = "Configuration for raspi01 status monitor"

name = "setup for the status monitor"
group = "special"

_expcolumn = Column(
    Block(
        "Experiment",
        [
            BlockRow(
                Field(name="Proposal", key="exp/proposal", width=10),
                Field(name="Title", key="exp/title", width=60, istext=True),
                Field(name="Current status", key="exp/action", width=30, istext=True),
            ),
            BlockRow(
                Field(
                    name="Sample",
                    key="sample/samplename",
                    width=50,
                    istext=True,
                    maxlen=50,
                ),
                Field(
                    name="Remark", key="exp/remark", width=50, istext=True, maxlen=50
                ),
            ),
        ],
    ),
)

_huberblock = SetupBlock("huber")

_servostarblock = SetupBlock("servostar")

_detectorikonlcolumn = Column(
    Block(
        "Detector Andor IkonL",
        [
            BlockRow(
                Field(name="Path", key="Exp/proposalpath", width=40, format="%s/"),
                Field(name="Last Image", key="exp/lastpoint", width=60),
            ),
            BlockRow(
                Field(name="Status", key="ikonl/status[1]", width=25),
                Field(name="Temp", dev="temp_ikonl"),
                Field(name="hsspeed", key="ikonl.hsspeed", width=4),
                Field(name="vsspeed", key="ikonl.vsspeed", width=4),
                Field(name="pgain", key="ikonl.pgain", width=4),
            ),
            BlockRow(
                Field(name="roi", key="ikonl.roi"),
                Field(name="bin", key="ikonl.bin"),
                Field(name="flip (H,V)", key="ikonl.flip"),
                Field(name="rotation", key="ikonl.rotation"),
            ),
        ],
        setups="detector_ikonl",
    ),
)

_detectorneocolumn = Column(
    Block(
        "Detector Andor Neo",
        [
            BlockRow(
                Field(name="Path", key="Exp/proposalpath", width=40, format="%s/"),
                Field(name="Last Image", key="exp/lastpoint", width=60),
            ),
            BlockRow(
                Field(name="Status", key="neo/status[1]", width=25),
                Field(dev="temp_neo"),
                Field(name="elshuttermode", key="neo.elshuttermode", width=6),
                Field(name="readoutrate MHz", key="neo.readoutrate", width=4),
            ),
            BlockRow(
                Field(name="roi", key="neo.roi"),
                Field(name="bin", key="neo.bin"),
                Field(name="flip (H,V)", key="neo.flip"),
                Field(name="rotation", key="neo.rotation"),
            ),
        ],
        setups="detector_neo",
    ),
)

_detectorzwo01column = Column(
    Block(
        "Detector ZWO 01",
        [
            BlockRow(
                Field(name="Path", key="Exp/proposalpath", width=40, format="%s/"),
                Field(name="Last Image", key="exp/lastpoint", width=60),
            ),
            BlockRow(
                Field(name="Status", key="zwo01/status[1]", width=25),
                Field(dev="temp_zwo01"),
            ),
            BlockRow(
                Field(name="roi", key="zwo01.roi"),
                Field(name="bin", key="zwo01.bin"),
                Field(name="flip (H,V)", key="zwo01.flip"),
                Field(name="rotation", key="zwo01.rotation"),
            ),
        ],
        setups="detector_zwo01",
    ),
)

_shutterblock = SetupBlock("basic", "shutters")

_basicblock = SetupBlock("basic", "basic")

_sblblock = SetupBlock("sbl")

_lblblock = SetupBlock("lbl")

_detector_translationblock = SetupBlock("detector_translation")


_leftcolumn = Column(
    _shutterblock,
    _basicblock,
)

_rightcolumn = Column(
    _sblblock,
    _lblblock,
    _huberblock,
    _servostarblock,
    _detector_translationblock,
)


devices = dict(
    Monitor=device(
        "nicos.services.monitor.qt.Monitor",
        description="Status Display",
        title="R2D2",  #'ANTARES Status Monitor raspi01'
        loglevel="info",
        cache="antareshw.antares.frm2.tum.de",
        prefix="nicos/",
        font="Luxi Sans",
        fontsize=15,
        valuefont="Monospace",
        padding=1,
        layout=[
            [_expcolumn],
            [_detectorikonlcolumn],
            [_detectorneocolumn],
            [_detectorzwo01column],
            [_leftcolumn, _rightcolumn],
        ],
    ),
)
