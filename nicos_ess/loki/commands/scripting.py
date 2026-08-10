from nicos import session
from nicos.commands import usercommand
from nicos.commands.measure import count, SetDetectors
from nicos.commands.device import maw
from nicos_ess.loki.commands.general import start_run, stop_run

__all__ = ["do_trans", "do_sans", "do_sans_trans"]


DURATION_TYPES = {"seconds", "mevents", "frames"}

M2_BM_POSITIONER = "m2_beam_monitor_positioner"
BEAMSTOP1_POSITIONER = "beamstop1_positioner"
JBI_DETECTOR = "jbi_detector"


@usercommand
def do_trans(duration, duration_type=None, monitor="monitor1_data"):
    if duration_type not in DURATION_TYPES:
        raise RuntimeError(f"duration type must be one of {DURATION_TYPES}")

    m2_beam_monitor_positioner = session.devices[M2_BM_POSITIONER]
    beamstop1_positioner = session.devices[BEAMSTOP1_POSITIONER]
    jbi_detector = session.devices[JBI_DETECTOR]

    print("Configuring beam path for TRANS measurement")
    maw(m2_beam_monitor_positioner, 'in-beam')
    maw(beamstop1_positioner, 'Parked')
    print("TRANS beam path configured")

    SetDetectors(jbi_detector)

    start_run()

    if duration_type == "seconds":
        count(t=duration)
    elif duration_type == "mevents":
        count(**{monitor: duration})
    else:
        raise NotImplementedError("frames/pulses not supported yet")

    print("TRANS measurement complete.")
    stop_run()


@usercommand
def do_sans(duration, duration_type=None, monitor="monitor1_data"):
    if duration_type not in DURATION_TYPES:
        raise RuntimeError(f"duration type must be one of {DURATION_TYPES}")

    m2_beam_monitor_positioner = session.devices[M2_BM_POSITIONER]
    beamstop1_positioner = session.devices[BEAMSTOP1_POSITIONER]
    jbi_detector = session.devices[JBI_DETECTOR]

    print("Configuring beam path for SANS measurement")
    maw(m2_beam_monitor_positioner, 'in-beam')
    maw(beamstop1_positioner, 'Parked')
    print("SANS beam path configured")

    SetDetectors(jbi_detector)

    start_run()

    if duration_type == "seconds":
        count(t=duration)
    elif duration_type == "mevents":
        count(**{monitor: duration})
    else:
        raise NotImplementedError("frames/pulses not supported yet")

    print("SANS measurement complete.")
    
    stop_run()


@usercommand
def do_sans_trans(duration, duration_type=None, monitor="monitor1_data"):
    if duration_type not in DURATION_TYPES:
        raise RuntimeError(f"duration type must be one of {DURATION_TYPES}")

    m2_beam_monitor_positioner = session.devices[M2_BM_POSITIONER]
    beamstop1_positioner = session.devices[BEAMSTOP1_POSITIONER]
    jbi_detector = session.devices[JBI_DETECTOR]

    print("Configuring beam path for SANS + TRANS measurement")
    maw(m2_beam_monitor_positioner, 'in-beam')
    maw(beamstop1_positioner, 'In beam')
    print("SANS + transmission beam path configured")

    SetDetectors(jbi_detector)

    start_run()

    if duration_type == "seconds":
        count(t=duration)
    elif duration_type == "mevents":
        count(**{monitor: duration})
    else:
        raise NotImplementedError("frames/pulses not supported yet")

    print("SANSTRANS measurement complete.")

    stop_run()
