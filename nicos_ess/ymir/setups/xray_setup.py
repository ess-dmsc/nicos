description  = "The X-ray setup that will be used for ODIN"

pv_root = "LabODIN-Xray:Ctrl-HV-01:"

devices = dict(
    # System & Device Information
    model_r=device(
        "nicos_ess.devices.epics.pva.EpicsStringReadable",
        description="Model Name Check",
        readpv="{}Model-R".format(pv_root),
    ),


    # Core status
    status_r=device(
        "nicos_ess.devices.epics.pva.EpicsMappedReadable",
        description="X-ray Source Status",
        readpv="{}Status-R".format(pv_root),
    ),
    beam_align_r=device(
        "nicos_ess.devices.epics.pva.EpicsMappedReadable",
        description="Beam Alignment Status",
        readpv="{}BeamAlign-R".format(pv_root),
    ),
    interlock_r=device(
        "nicos_ess.devices.epics.pva.EpicsMappedReadable",
        description="Interlock Status",
        readpv="{}Interlock-R".format(pv_root),
    ),


    # Operational commands
    xray=device(
        "nicos_ess.devices.epics.pva.EpicsMappedMoveable",
        description="X-ray ON/OFF Control",
        readpv="{}XRay-S".format(pv_root),
        writepv="{}XRay-S".format(pv_root),
    ),
    warmup=device(
        "nicos_ess.devices.epics.pva.EpicsMappedMoveable",
        description="Start Warmup",
        readpv="{}Warmup-S".format(pv_root),
        writepv="{}Warmup-S".format(pv_root),
    ),
    reset=device(
        "nicos_ess.devices.epics.pva.EpicsMappedMoveable",
        description="Reset Overload Protection",
        readpv="{}Reset-S".format(pv_root),
        writepv="{}Reset-S".format(pv_root),
    ),


    # Tube Voltage (20 - 300 kV)
    voltage=device(
        "nicos_ess.devices.epics.pva.EpicsAnalogMoveable", #might change to digital
        description="Set Tube Voltage",
        readpv="{}Voltage-RB".format(pv_root),
        writepv="{}Voltage-S".format(pv_root),
        abslimits=(20, 300),
    ),
    voltage_r=device(
        "nicos_ess.devices.epics.pva.EpicsNumericReadable",
        description="Output Tube Voltage Check",
        readpv="{}Voltage-R".format(pv_root)
    ),


    # Tube Current (0 - 1000 uA)
    current=device(
        "nicos_ess.devices.epics.pva.EpicsAnalogMoveable", #might change to digital
        description="Set Tube Current",
        readpv="{}Current-RB".format(pv_root),
        writepv="{}Current-S".format(pv_root),
        abslimits=(0, 1000),
    ),
    current_r=device(
        "nicos_ess.devices.epics.pva.EpicsNumericReadable",
        description="Output Tube Current Check",
        readpv="{}Current-R".format(pv_root)
    ),


    # Focus Settings (0 - 23000)
    focus=device(
        "nicos_ess.devices.epics.pva.EpicsAnalogMoveable", #might change to digital
        description="Set Focus Value",
        readpv="{}Focus-RB".format(pv_root),
        writepv="{}Focus-S".format(pv_root),
        abslimits=(0, 23000),
    ),
    

    # Environment/Misc Monitoring
    vacuum_r=device(
        "nicos_ess.devices.epics.pva.EpicsNumericReadable",
        description="Vacuum Level Check",
        readpv="{}Vacuum-R".format(pv_root)
    ),
    temperature_r=device(
        "nicos_ess.devices.epics.pva.EpicsNumericReadable",
        description="Temperature Check",
        readpv="{}Temperature-R".format(pv_root)
    ),


    # X/Y Object Alignment Settings (-1200 to 1200)
    align_x=device(
        "nicos_ess.devices.epics.pva.EpicsAnalogMoveable", #might change to digital
        description="Set X-dir Object Align",
        readpv="{}AlignX-RB".format(pv_root),
        writepv="{}AlignX-S".format(pv_root),
        abslimits=(-1200,1200),
    ),
    align_y=device(
        "nicos_ess.devices.epics.pva.EpicsAnalogMoveable", #might change to digital
        description="Set Y-dir Object Align",
        readpv="{}AlignY-RB".format(pv_root),
        writepv="{}AlignY-S".format(pv_root),
        abslimits=(-1200,1200),
    ),


    # Alignment Execution Commands
    align_beam=device(
        "nicos_ess.devices.epics.pva.EpicsMappedMoveable",
        description="Start Beam Alignment",
        readpv="{}AlignBeam-S".format(pv_root),
        writepv="{}AlignBeam-S".format(pv_root),
    ),
    align_all=device(
        "nicos_ess.devices.epics.pva.EpicsMappedMoveable",
        description="Start Overall Alignment",
        readpv="{}AlignAll-S".format(pv_root),
        writepv="{}AlignAll-S".format(pv_root),
    ),
    align_stop=device(
        "nicos_ess.devices.epics.pva.EpicsMappedMoveable",
        description="Stop Beam Alignment",
        readpv="{}AlignStop-S".format(pv_root),
        writepv="{}AlignStop-S".format(pv_root),
    ),
)