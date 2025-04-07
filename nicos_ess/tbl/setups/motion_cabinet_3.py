description = "Motion cabinet 3"

devices = dict(
    mc_pne_315=device(
        "nicos_ess.devices.epics.pva.shutter.EpicsShutter",
        description="Motion control pneumatic axis #315",
        readpv="TBL-TBL:MC-Pne-315:ShtAuxBits07",
        writepv="TBL-TBL:MC-Pne-315:ShtOpen",
        pva=True,
        monitor=True,
        pollinterval=0.5,
        maxage=None,
    ),
    mc_pne_315_status=device(
        "nicos_ess.devices.epics.pva.EpicsStringReadable",
        description="Status of the motion control pneumatic axis #315",
        readpv="TBL-TBL:MC-Pne-315:ShtMsgTxt",
    ),
    mc_pne_316=device(
        "nicos_ess.devices.epics.pva.shutter.EpicsShutter",
        description="Motion control pneumatic axis #316",
        readpv="TBL-TBL:MC-Pne-316:ShtAuxBits07",
        writepv="TBL-TBL:MC-Pne-316:ShtOpen",
        pva=True,
        monitor=True,
        pollinterval=0.5,
        maxage=None,
    ),
    mc_pne_316_status=device(
        "nicos_ess.devices.epics.pva.EpicsStringReadable",
        description="Status of the motion control pneumatic axis #316",
        readpv="TBL-TBL:MC-Pne-316:ShtMsgTxt",
    ),
    mc_mtr_301=device(
        "nicos_ess.devices.epics.pva.motor.EpicsMotor",
        description="Motion control electrical axis #301",
        motorpv="TBL-TBL:MC-Pos-301:Mtr",
        monitor_deadband=0.01,
    ),
    mc_mtr_302=device(
        "nicos_ess.devices.epics.pva.motor.EpicsMotor",
        description="Motion control electrical axis #302",
        motorpv="TBL-TBL:MC-Pos-302:Mtr",
        monitor_deadband=0.01,
    ),
    mc_mtr_303=device(
        "nicos_ess.devices.epics.pva.motor.EpicsMotor",
        description="Motion control electrical axis #303",
        motorpv="TBL-TBL:MC-Pos-303:Mtr",
        monitor_deadband=0.01,
    ),
    mc_mtr_304=device(
        "nicos_ess.devices.epics.pva.motor.EpicsMotor",
        description="Motion control electrical axis #304",
        motorpv="TBL-TBL:MC-Pos-304:Mtr",
        monitor_deadband=0.01,
    ),
    mc_mtr_305=device(
        "nicos_ess.devices.epics.pva.motor.EpicsMotor",
        description="Motion control electrical axis #305",
        motorpv="TBL-TBL:MC-Pos-305:Mtr",
        monitor_deadband=0.01,
    ),
    mc_mtr_306=device(
        "nicos_ess.devices.epics.pva.motor.EpicsMotor",
        description="Motion control electrical axis #306",
        motorpv="TBL-TBL:MC-Pos-306:Mtr",
        monitor_deadband=0.01,
    ),
    mc_mtr_307=device(
        "nicos_ess.devices.epics.pva.motor.EpicsMotor",
        description="Motion control electrical axis #307",
        motorpv="TBL-TBL:MC-Pos-307:Mtr",
        monitor_deadband=0.01,
    ),
    mc_mtr_308=device(
        "nicos_ess.devices.epics.pva.motor.EpicsMotor",
        description="Motion control electrical axis #308",
        motorpv="TBL-TBL:MC-Pos-308:Mtr",
        monitor_deadband=0.01,
    ),
    mc_mtr_309=device(
        "nicos_ess.devices.epics.pva.motor.EpicsMotor",
        description="Motion control electrical axis #309",
        motorpv="TBL-TBL:MC-Pos-309:Mtr",
        monitor_deadband=0.01,
    ),
    mc_mtr_310=device(
        "nicos_ess.devices.epics.pva.motor.EpicsMotor",
        description="Motion control electrical axis #310",
        motorpv="TBL-TBL:MC-Pos-310:Mtr",
        monitor_deadband=0.01,
    ),
    mc_mtr_311=device(
        "nicos_ess.devices.epics.pva.motor.EpicsMotor",
        description="Motion control electrical axis #311",
        motorpv="TBL-TBL:MC-Pos-311:Mtr",
        monitor_deadband=0.01,
    ),
    mc_mtr_312=device(
        "nicos_ess.devices.epics.pva.motor.EpicsMotor",
        description="Motion control electrical axis #312",
        motorpv="TBL-TBL:MC-Pos-312:Mtr",
        monitor_deadband=0.01,
    ),
    mc_mtr_313=device(
        "nicos_ess.devices.epics.pva.motor.EpicsMotor",
        description="Motion control electrical axis #313",
        motorpv="TBL-TBL:MC-Pos-313:Mtr",
        monitor_deadband=0.01,
    ),
    mc_mtr_314=device(
        "nicos_ess.devices.epics.pva.motor.EpicsMotor",
        description="Motion control electrical axis #314",
        motorpv="TBL-TBL:MC-Pos-314:Mtr",
        monitor_deadband=0.01,
    )
)