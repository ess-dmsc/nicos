description = "NMX Collimation System"

pv_root = "NMX"
slit_set_1_pv_root = f"{pv_root}-ColSl1:"
slit_set_2_pv_root = f"{pv_root}-ColSl2:"
pinhole_exchanger_pv_root= f"{pv_root}-PinChg:"

# TODO: Check descriptions (axis and cabinet numbers)!

devices = dict(
    # Slit 1 blades
    slit_set_1_left_blade=device(
        "nicos_ess.devices.epics.pva.motor.EpicsMotor",
        description="Collimation slit set 1 left blade - electrical axis 1 in motion cabinet 2",
        motorpv=f"{slit_set_1_pv_root}MC-SlYp-01:Mtr",
        monitor_deadband=0.01,
        visibility={},
    ),
    slit_set_1_right_blade=device(
        "nicos_ess.devices.epics.pva.motor.EpicsMotor",
        description="Collimation slit set 1 right blade - electrical axis 2 in motion cabinet 2",
        motorpv=f"{slit_set_1_pv_root}MC-SlYm-01:Mtr",
        monitor_deadband=0.01,
        visibility={},
    ),
    slit_set_1_upper_blade=device(
        "nicos_ess.devices.epics.pva.motor.EpicsMotor",
        description="Collimation slit set 1 upper blade - electrical axis 3 in motion cabinet 2",
        motorpv=f"{slit_set_1_pv_root}MC-SlZp-01:Mtr",
        monitor_deadband=0.01,
        visibility={},
    ),
    slit_set_1_lower_blade=device(
        "nicos_ess.devices.epics.pva.motor.EpicsMotor",
        description="Collimation slit set 1 lower blade - electrical axis 4 in motion cabinet 2",
        motorpv=f"{slit_set_1_pv_root}MC-SlZm-01:Mtr",
        monitor_deadband=0.01,
        visibility={},
    ),
    # Slit 1 center and gap
    slit_set_1_horizontal_center=device(
        "nicos_ess.devices.epics.pva.motor.EpicsMotor",
        description="Collimation slit set 1 horizontal center",
        motorpv=f"{slit_set_1_pv_root}MC-SlYc-01:Mtr",
        monitor_deadband=0.01,
    ),
    slit_set_1_horizontal_gap=device(
        "nicos_ess.devices.epics.pva.motor.EpicsMotor",
        description="Collimation slit set 1 horizontal gap",
        motorpv=f"{slit_set_1_pv_root}MC-SlYg-01:Mtr",
        monitor_deadband=0.01,
    ),
    slit_set_1_vertical_center=device(
        "nicos_ess.devices.epics.pva.motor.EpicsMotor",
        description="Collimation slit set 1 vertical center",
        motorpv=f"{slit_set_1_pv_root}MC-SlZc-01:Mtr",
        monitor_deadband=0.01,
    ),
    slit_set_1_vertical_gap=device(
        "nicos_ess.devices.epics.pva.motor.EpicsMotor",
        description="Collimation slit set 1 vertical gap",
        motorpv=f"{slit_set_1_pv_root}MC-SlZg-01:Mtr",
        monitor_deadband=0.01,
    ),
    # Slit 2 blades
    slit_set_2_left_blade=device(
        "nicos_ess.devices.epics.pva.motor.EpicsMotor",
        description="Collimation slit set 2 left blade - electrical axis 5 in motion cabinet 2",
        motorpv=f"{slit_set_2_pv_root}MC-SlYp-01:Mtr",
        monitor_deadband=0.01,
        visibility={},
    ),
    slit_set_2_right_blade=device(
        "nicos_ess.devices.epics.pva.motor.EpicsMotor",
        description="Collimation slit set 2 right blade - electrical axis 6 in motion cabinet 2",
        motorpv=f"{slit_set_2_pv_root}MC-SlYm-01:Mtr",
        monitor_deadband=0.01,
        visibility={},
    ),
    slit_set_2_upper_blade=device(
        "nicos_ess.devices.epics.pva.motor.EpicsMotor",
        description="Collimation slit set 2 upper blade - electrical axis 7 in motion cabinet 2",
        motorpv=f"{slit_set_2_pv_root}MC-SlZp-01:Mtr",
        monitor_deadband=0.01,
        visibility={},
    ),
    slit_set_2_lower_blade=device(
        "nicos_ess.devices.epics.pva.motor.EpicsMotor",
        description="Collimation slit set 2 lower blade - electrical axis 8 in motion cabinet 2",
        motorpv=f"{slit_set_2_pv_root}MC-SlZm-01:Mtr",
        monitor_deadband=0.01,
        visibility={},
    ),
    # Slit 2 center and gap
    slit_set_2_horizontal_center=device(
        "nicos_ess.devices.epics.pva.motor.EpicsMotor",
        description="Collimation slit set 2 horizontal center",
        motorpv=f"{slit_set_2_pv_root}MC-SlYc-01:Mtr",
        monitor_deadband=0.01,
    ),
    slit_set_2_horizontal_gap=device(
        "nicos_ess.devices.epics.pva.motor.EpicsMotor",
        description="Collimation slit set 2 horizontal gap",
        motorpv=f"{slit_set_2_pv_root}MC-SlYg-01:Mtr",
        monitor_deadband=0.01,
    ),
    slit_set_2_vertical_center=device(
        "nicos_ess.devices.epics.pva.motor.EpicsMotor",
        description="Collimation slit set 2 vertical center",
        motorpv=f"{slit_set_2_pv_root}MC-SlZc-01:Mtr",
        monitor_deadband=0.01,
    ),
    slit_set_2_vertical_gap=device(
        "nicos_ess.devices.epics.pva.motor.EpicsMotor",
        description="Collimation slit set 2 vertical gap",
        motorpv=f"{slit_set_2_pv_root}MC-SlZg-01:Mtr",
        monitor_deadband=0.01,
    ),
    # Pinhole
    pinhole_exchanger__motor=device(
        "nicos_ess.devices.epics.pva.motor.EpicsMotor",
        description="Pinhole exchanger (as a motor)",
        motorpv=f"{pinhole_exchanger_pv_root}MC-Pin-01:Mtr",
        monitor_deadband=0.01, # TODO: Remove this?
        visibility={},
    ),
    pinhole_exchanger__mount_pinhole=device(
        "nicos_ess.devices.epics.pva.EpicsManualMappedAnalogMoveable",
        description="Mount a selected pinhole (or have no pinhole mounted)",
        readpv=f"{pinhole_exchanger_pv_root}MC-Pin-01:Mtr.RBV",
        writepv=f"{pinhole_exchanger_pv_root}MC-Pin-01:Mtr.VAL",
        precision=0.0, # TODO: Is it right? Or should we remove this?
        mapping={"Pinhole 0": 0, "Pinhole 1": 1, "Pinhole 2": 2, "Pinhole 3": 3, "No pinhole (unmount)": 11}, # Value "11" unmounts. TODO: Add all pins.
        fmtstr="%d",
    ),
    # Bits: B0..B19
    # TODO: Find a better device for this!
    pinhole_exchanger__current_pinhole=device(
        "nicos_ess.devices.epics.mbbi_direct.MBBIDirectStatus",
        description="Pinhole exchanger mounted pin",
        pv_root=f"{pinhole_exchanger_pv_root}MC-Pin-01:Mtr-StatusBits",
        number_of_bits=11,
    ),
    pinhole_exchanger__status_bit0=device(
        "nicos_ess.devices.epics.pva.EpicsReadable",
        description="Pinhole status bit 0",
        readpv=f"{pinhole_exchanger_pv_root}MC-Pin-01:Mtr-StatusBits.B0",
        fmtstr="%d",
    ),
    pinhole_exchanger__status_bit1=device(
        "nicos_ess.devices.epics.pva.EpicsReadable",
        description="Pinhole status bit 1",
        readpv=f"{pinhole_exchanger_pv_root}MC-Pin-01:Mtr-StatusBits.B1",
        fmtstr="%d",
    ),
)
