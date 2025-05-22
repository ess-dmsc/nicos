# ruff: noqa: F821
description = "General Cryo Magnet Setup"

pv_root = "SE-VM2:Magnet:"

devices = dict(
    actual_value=device(
        "nicos_ess.devices.epics.pva.EpicsAnalogReadable",
        description="Actual value of IPS",
        readpv=pv_root + "value-R",
    ),
    target_value=device(
        "nicos_ess.devices.epics.pva.EpicsAnalogMoveable",
        description="Ramp target value of IPS",
        readpv=pv_root + "target-R",
        writepv=pv_root + "target-S",
    ),
    actual_ramp_speed=device(
        "nicos_ess.devices.epics.pva.EpicsAnalogMoveable",
        description="Actual ramp speed of IPS",
        readpv=pv_root + "_ramp-R",
        writepv=pv_root + "_ramp-S",
    ),
    use_ramp_speed=device(
        "nicos_ess.devices.epics.manual_switch.ManualSwitch",
        description="Use defined ramp speed to approach target value of IPS",
        readpv=pv_root + "_use_ramp-R",
        writepv=pv_root + "_use_ramp-S",
        pollinterval=0.5,
        monitor=True,
        pva=True,
        states=["False", "True"],
        mapping={"False": 0, "True": 1},
    ),
    ramp_setpoint=device(
        "nicos_ess.devices.epics.pva.EpicsAnalogReadable",
        description="Actual target value in ramp of IPS",
        readpv=pv_root + "_ramp_setpoint-R",
    ),
    time_to_target=device(
        "nicos_ess.devices.epics.pva.EpicsAnalogReadable",
        description="Expected time to target of IPS",
        readpv=pv_root + "_time_to_target-R",
    ),
    stop=device(
        "nicos_ess.devices.epics.pva.EpicsStringReadable",
        description="Stop the ramp of IPS",
        readpv=pv_root + "stop-R",
    ),
    prepare=device(
        "nicos_ess.devices.epics.pva.EpicsStringReadable",
        description="Prepare the ramp of IPS",
        readpv=pv_root + "_prepare-R",
    ),
    go=device(
        "nicos_ess.devices.epics.manual_switch.ManualSwitch",
        description="Start the ramp of IPS",
        readpv=pv_root + "go-R",
        writepv=pv_root + "go-S",
        states=["False", "True"],
        mapping={"False": 0, "True": 1},
        pollinterval=0.5,
        monitor=True,
        pva=True,
    ),
    abort=device(
        "nicos_ess.devices.epics.pva.EpicsStringReadable",
        description="Abort the ramp of IPS",
        readpv=pv_root + "abort-R",
    ),
    shutdown=device(
        "nicos_ess.devices.epics.pva.EpicsStringReadable",
        description="Set the magnet to 0T of IPS",
        readpv=pv_root + "shutdown-R",
    ),
    persistent_mode=device(
        "nicos_ess.devices.epics.manual_switch.ManualSwitch",
        description="Set persistent mode after ramp of IPS",
        readpv=pv_root + "_go_persistent-R",
        writepv=pv_root + "_go_persistent-S",
        states=["False", "True"],
        mapping={"False": 0, "True": 1},
        pollinterval=0.5,
        monitor=True,
        pva=True,
    ),
    magnet_persistent=device(
        "nicos_ess.devices.epics.pva.EpicsStringReadable",
        description="Magnet in Persistent mode of IPS",
        readpv=pv_root + "_persistent-R",
    ),
    switch_status=device(
        "nicos_ess.devices.epics.pva.EpicsAnalogReadable",
        description="Switch heater status of IPS",
        readpv=pv_root + "_switchstatus-R",
    ),
    output_of_powersupply=device(
        "nicos_ess.devices.epics.pva.EpicsAnalogReadable",
        description="Returns the power supply output field of IPS",
        readpv=pv_root + "_output_of_powersupply-R",
    ),
    magnet_ips_status=device(
        "nicos_ess.devices.epics.pva.EpicsStringReadable",
        description="Status of the IPS",
        readpv=pv_root + "status-R",
    ),
)
