from nicos import session
from nicos.commands import usercommand
from nicos.commands.basic import sleep
from nicos.commands.device import maw
from nicos_ess.commands.filewriter import start_filewriting, stop_filewriting

__all__ = ["check_run_conditions", "start_run", "stop_run"]

GATE_VALVE = "gate_valve"
HEAVY_SHUTTER = "heavy_shutter"
WINDOW_GUARD = "window_guard"
ALIGNMENT_LASER_MIRROR = "alignment_laser_mirror"
ALIGNMENT_LASER_MIRROR_POSITIONER = "alignment_laser_mirror_positioner"
EXPERIMENT_SHUTTER = "experiment_shutter"


@usercommand
def check_run_conditions():
    """Verify that all required conditions are satisfied before data
    acquisition.

    Blocks untils run conditions are satisfied.

    Conditions checked:
      - Gate valve open
      - Heavy shutter open

    Notes:
      - This function does not move hardware.
      - Hardware preparation is handled by start_run().
    """
    print("Checking run conditions before data acquisition")
    
    gate_valve = session.devices[GATE_VALVE]
    heavy_shutter = session.devices[HEAVY_SHUTTER]

    while True:
        conditions_ok = True

        # Check gate valve
        gate_valve_status = gate_valve.read()

        if gate_valve_status != "OPEN":
            print(
                f"Gate valve status: {gate_valve_status}. "
                "Waiting for gate valve to open..."
            )
            conditions_ok = False

        # Check heavy shutter status
        heavy_shutter_status = heavy_shutter.read()

        if heavy_shutter_status != "Open":
            print(
                f"Heavy shutter status: {heavy_shutter_status}. "
                "Waiting for heavy shutter to open..."
            )
            conditions_ok = False

        if conditions_ok:
            print("Run conditions satisfied")
            break

        sleep(5)


@usercommand
def start_run():
    """Prepare LoKI for data acquisition and start file writing.

     Actions:
      - Open window guard
      - Move alignment mirror out of beam
      - Open experiment/fast shutter
      - Verify run conditions
      - Start file writing

    Notes:
      - Hardware is automatically moved to the required position.
      - Run conditions are verified by check_run_conditions().
    """
    print("Preparing LoKI for measurement")

    # Open window guard
    window_guard = session.devices[WINDOW_GUARD]
    if window_guard.read() != "Open":
        print("Opening window guard...")
        maw(window_guard, "Open")

    # Move alignment mirror out of beam
    alignment_laser_mirror = session.devices[ALIGNMENT_LASER_MIRROR]
    alignment_laser_mirror_positioner = session.devices[ALIGNMENT_LASER_MIRROR_POSITIONER]
    if (
        alignment_laser_mirror.read()
        != alignment_laser_mirror_positioner.mapping["out-of-beam"]
    ):
        print("Moving alignment mirror out of beam...")
        maw(alignment_laser_mirror_positioner, "out-of-beam")

    # Open experiment/fast shutter
    experiment_shutter = session.devices[EXPERIMENT_SHUTTER]
    if experiment_shutter.read() != "Open":
        print("Opening experiment/fast shutter...")
        maw(experiment_shutter, "Open")

    # Verify run conditions
    check_run_conditions()

    # Start file writing
    print("Starting file writing...")
    start_filewriting()

    print("LoKI ready for measurement")


@usercommand
def stop_run():
    """Stop file writing & close fast shutter."""
    print("Stopping file writing...")
    stop_filewriting()

    print("Closing experiment/fast shutter...")
    experiment_shutter = session.devices[EXPERIMENT_SHUTTER]
    maw(experiment_shutter, "Closed")

    print("Run complete")
