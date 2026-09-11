description = "The X-ray setup that will be used for ODIN"

pv_root = "LabODIN-Xray:Ctrl-HV-01:"

devices = dict(
    # System & Device Information
    model_r=device(
        "nicos_ess.devices.epics.pva.EpicsStringReadable",
        description="Model Name Check",
        readpv=f"{pv_root}Model-R",
    ),
    # Core status
    status_r=device(
        "nicos_ess.devices.epics.pva.EpicsMappedReadable",
        description="X-ray Source Status",
        readpv=f"{pv_root}Status-R",
    ),
    beam_align_r=device(
        "nicos_ess.devices.epics.pva.EpicsMappedReadable",
        description="Beam Alignment Status",
        readpv=f"{pv_root}BeamAlign-R",
    ),
    interlock_r=device(
        "nicos_ess.devices.epics.pva.EpicsMappedReadable",
        description="Interlock Status",
        readpv=f"{pv_root}Interlock-R",
    ),
    # Operational commands
    xray=device(
        "nicos_ess.devices.epics.pva.EpicsMappedMoveable",
        description="X-ray ON/OFF Control",
        readpv=f"{pv_root}XRay-S",
        writepv=f"{pv_root}XRay-S",
    ),
    warmup=device(
        "nicos_ess.devices.epics.pva.EpicsMappedMoveable",
        description="Start Warmup",
        readpv=f"{pv_root}Warmup-S",
        writepv=f"{pv_root}Warmup-S",
    ),
    reset=device(
        "nicos_ess.devices.epics.pva.EpicsMappedMoveable",
        description="Reset Overload Protection",
        readpv=f"{pv_root}Reset-S",
        writepv=f"{pv_root}Reset-S",
    ),
    # Tube Voltage (20 - 300 kV)
    voltage=device(
        "nicos_ess.devices.epics.pva.EpicsAnalogMoveable",  # might change to digital
        description="Set Tube Voltage",
        readpv=f"{pv_root}Voltage-RB",
        writepv=f"{pv_root}Voltage-S",
        abslimits=(20, 300),
    ),
    voltage_r=device(
        "nicos_ess.devices.epics.pva.EpicsNumericReadable",
        description="Output Tube Voltage Check",
        readpv=f"{pv_root}Voltage-R",
    ),
    # Tube Current (0 - 1000 uA)
    current=device(
        "nicos_ess.devices.epics.pva.EpicsAnalogMoveable",  # might change to digital
        description="Set Tube Current",
        readpv=f"{pv_root}Current-RB",
        writepv=f"{pv_root}Current-S",
        abslimits=(0, 1000),
    ),
    current_r=device(
        "nicos_ess.devices.epics.pva.EpicsNumericReadable",
        description="Output Tube Current Check",
        readpv=f"{pv_root}Current-R",
    ),
    # Focus Settings (0 - 23000)
    focus=device(
        "nicos_ess.devices.epics.pva.EpicsAnalogMoveable",  # might change to digital
        description="Set Focus Value",
        readpv=f"{pv_root}Focus-RB",
        writepv=f"{pv_root}Focus-S",
        abslimits=(0, 23000),
    ),
    # Environment/Misc Monitoring
    vacuum_r=device(
        "nicos_ess.devices.epics.pva.EpicsNumericReadable",
        description="Vacuum Level Check",
        readpv=f"{pv_root}Vacuum-R",
    ),
    temperature_r=device(
        "nicos_ess.devices.epics.pva.EpicsNumericReadable",
        description="Temperature Check",
        readpv=f"{pv_root}Temperature-R",
    ),
    # X/Y Object Alignment Settings (-1200 to 1200)
    align_x=device(
        "nicos_ess.devices.epics.pva.EpicsAnalogMoveable",  # might change to digital
        description="Set X-dir Object Align",
        readpv=f"{pv_root}AlignX-RB",
        writepv=f"{pv_root}AlignX-S",
        abslimits=(-1200, 1200),
    ),
    align_y=device(
        "nicos_ess.devices.epics.pva.EpicsAnalogMoveable",  # might change to digital
        description="Set Y-dir Object Align",
        readpv=f"{pv_root}AlignY-RB",
        writepv=f"{pv_root}AlignY-S",
        abslimits=(-1200, 1200),
    ),
    # Alignment Execution Commands
    align_beam=device(
        "nicos_ess.devices.epics.pva.EpicsMappedMoveable",
        description="Start Beam Alignment",
        readpv=f"{pv_root}AlignBeam-S",
        writepv=f"{pv_root}AlignBeam-S",
    ),
    align_all=device(
        "nicos_ess.devices.epics.pva.EpicsMappedMoveable",
        description="Start Overall Alignment",
        readpv=f"{pv_root}AlignAll-S",
        writepv=f"{pv_root}AlignAll-S",
    ),
    align_stop=device(
        "nicos_ess.devices.epics.pva.EpicsMappedMoveable",
        description="Stop Beam Alignment",
        readpv=f"{pv_root}AlignStop-S",
        writepv=f"{pv_root}AlignStop-S",
    ),
    # Virtual motors (to be replaced with real ones)
    source_motor=device(
        "nicos.devices.generic.virtual.VirtualMotor",
        description="Source Motor",
        abslimits=(0, 100),
        curvalue=0,
        unit="mm",
        speed=5.0,
    ),
    flatpanel_motor=device(
        "nicos.devices.generic.virtual.VirtualMotor",
        description="Detector/Flat Panel Motor",
        abslimits=(0, 100),
        curvalue=0,
        unit="mm",
        speed=5.0,
    ),
    # Filter menu
    filter_menu=device(
        "nicos_ess.devices.filter.FilterMenu",
        description="Filter Menu",
    ),
)
