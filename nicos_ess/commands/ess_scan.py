import time
from nicos import session
from nicos.commands import helparglist, usercommand
from nicos.core import (
    Device,
    Moveable,
    UsageError,
    Readable,
    Measurable,
    waitForCompletion,
)
from nicos.core.spm import Bare, Dev, spmsyntax
from nicos.core.utils import multiWait
from nicos.commands.basic import sleep
from nicos.utils import number_types
from nicos_ess.commands import waitfor_stable
from nicos.core.constants import SIMULATION
from nicos.core.errors import NicosError


def mkpos(starts, steps, numpoints):
    """Generate a list of positions for devices."""
    return [
        [start + i * step for (start, step) in zip(starts, steps)]
        for i in range(numpoints)
    ]


def parse_devices_and_positions(dev, args):
    """
    Parse devices and positions from the given arguments.

    Returns:
        devs: list of devices
        values: list of positions
        restargs: list of remaining arguments
    """
    if not args:
        raise UsageError("At least two arguments are required")

    if isinstance(dev, (list, tuple)):
        devs = dev
        if not isinstance(args[0], (list, tuple)):
            raise UsageError("Positions must be a list if devices are a list")

        if isinstance(args[0][0], (list, tuple)):
            # Positions given as list of lists
            for pos_list in args[0]:
                if len(pos_list) != len(args[0][0]):
                    raise UsageError(
                        "All position lists must have the same number of entries"
                    )
            values = list(zip(*args[0]))
            restargs = args[1:]
        else:
            # Start-step-numpoints mode
            if len(args) < 3:
                raise UsageError(
                    "At least four arguments are required in "
                    "start-step-numpoints scan command"
                )
            if not (
                isinstance(args[0], (list, tuple))
                and isinstance(args[1], (list, tuple))
            ):
                raise UsageError("Start and step must be lists")
            if not len(dev) == len(args[0]) == len(args[1]):
                raise UsageError("Start and step lists must be of equal length")
            values = mkpos(args[0], args[1], args[2])
            restargs = args[3:]
    else:
        devs = [dev]
        if isinstance(args[0], (list, tuple)):
            # Positions given as list
            values = list(zip(args[0]))
            restargs = args[1:]
        else:
            # Start-step-numpoints mode
            if len(args) < 3:
                raise UsageError(
                    "At least four arguments are required "
                    "in start-step-numpoints scan command"
                )
            values = mkpos([args[0]], [args[1]], args[2])
            restargs = args[3:]

    devs = [session.getDevice(d, Moveable) for d in devs]
    return devs, values, restargs


def _handleScanArgs(args, kwargs, scaninfo):
    preset, detlist, envlist, move, multistep = {}, None, None, [], []
    for arg in args:
        if isinstance(arg, str):
            scaninfo = arg + " - " + scaninfo
        elif isinstance(arg, number_types):
            preset["t"] = arg
        elif isinstance(arg, Measurable):
            if detlist is None:
                detlist = []
            detlist.append(arg)
        elif isinstance(arg, Readable):
            if envlist is None:
                envlist = []
            envlist.append(arg)
        else:
            raise UsageError("unsupported scan argument: %r" % arg)
    for key, value in kwargs.items():
        if key in session.devices and isinstance(session.devices[key], Moveable):
            # Here, don't replace 'list' by '(list, tuple)'
            # (tuples are reserved for valid device values)
            if isinstance(value, list):
                if multistep and len(value) != len(multistep[-1][1]):
                    raise UsageError(
                        "all multi-step arguments must have the " "same length"
                    )
                multistep.append((session.devices[key], value))
            else:
                move.append((session.devices[key], value))
        elif key == "info" and isinstance(value, str):
            scaninfo = value + " - " + scaninfo
        else:
            preset[key] = value
    return preset, scaninfo, detlist, envlist, move, multistep


def move_devices_to_positions(positions_dict):
    """Move devices to specified positions."""
    session.log.info("Moving devices to positions: %s", positions_dict)
    for dev, pos in positions_dict.items():
        try:
            dev.move(pos)
        except NicosError as err:
            session.log.error(
                "Error moving device %s to position %s: %s", dev.name, pos, err
            )
            raise err


def wait_for_devices(devices):
    """Wait for devices to reach their target positions."""
    try:
        multiWait(devices)
    except NicosError as err:
        session.log.error("Error waiting for devices: %s", err)
        raise err


def wait_for_stability(positions_dict, accuracy, time_stable, timeout):
    """Wait for devices to stabilize at their target positions."""
    for dev, pos in positions_dict.items():
        waitfor_stable(dev, pos, accuracy, time_stable, timeout)


def start_detectors(detectors, preset):
    """Start detectors."""
    session.log.info("Starting detectors")
    for det in detectors:
        det.setPreset(**preset)

    for det in detectors:
        det.prepare()

    for det in detectors:
        waitForCompletion(det)

    for det in detectors:
        det.start()


def wait_for_detectors(detectors):
    """Wait for detectors to complete their measurements."""
    detset = set(detectors)
    delay = (
        session.instrument and session.instrument.countloopdelay or 0.025
        if session.mode != SIMULATION
        else 0.0
    )
    try:
        while detset:
            for det in list(detset):
                if det.isCompleted():
                    det.finish()
                    detset.discard(det)
            session.delay(delay)
    except Exception as e:
        session.log.error("Error during detector waiting: %s", e)
        for det in detset:
            det.stop()
        raise e


def emit_scan_start_event(info_dict):
    """Emit the scan_start_event."""
    session.emitfunc("scan_start_event", info_dict)


def emit_scan_end_event(info_dict):
    """Emit the scan_end_event."""
    session.emitfunc("scan_end_event", info_dict)


@usercommand
@helparglist("dev, [start, step, numpoints | listofpoints], ...")
@spmsyntax(Dev(Moveable), Bare, Bare, Bare)
def ess_scan(dev, *args, **kwargs):
    """ess_scan."""
    # Parse the devices and positions
    devs, values, restargs = parse_devices_and_positions(dev, args)

    # Handle additional arguments
    scaninfo = ""
    sleep_time = kwargs.pop("sleep", 1)
    accuracy = kwargs.pop("accuracy", None)
    time_stable = kwargs.pop("time_stable", None)
    timeout = kwargs.pop("timeout", 3600)  # Default timeout for stability checks

    scaninfo = kwargs.pop("info", scaninfo)

    preset, scaninfo, detlist, envlist, _, _ = _handleScanArgs(
        restargs, kwargs, scaninfo
    )

    if detlist is None:
        detlist = session.experiment.detectors
        if not detlist:
            session.log.warning(
                "No detectors specified and no default detectors set. "
                "Use SetDetectors() to select detectors."
            )
    else:
        detlist = [session.getDevice(d, Device) for d in detlist]

    session.log.warning(f"Detectors: {detlist} with preset: {preset}")

    if detlist and preset:
        names = set(preset)
        for det in detlist:
            names.difference_update(det.presetInfo())
        if names:
            session.log.warning(
                "these preset keys were not recognized by "
                "any of the detectors: %s -- detectors are"
                " %s",
                ", ".join(names),
                ", ".join(map(str, detlist)),
            )
    if preset is None:
        preset = {}
    if not preset:
        for det in detlist:
            preset.update(det.preset())

    # add all the channels from the detectors do the list of additional devices
    additional_devices = []
    for det in detlist:
        value_info = det.valueInfo()
        for value in value_info:
            try:
                channel_name = value.name
                session.log.warning(
                    f"Adding channel {channel_name} to additional devices"
                )
                additional_devices.append(session.getDevice(channel_name, Readable))
            except Exception as e:
                session.log.error(e)

    # Move devices to initial positions
    initial_positions = values[0]
    positions_dict = dict(zip(devs, initial_positions))
    move_devices_to_positions(positions_dict)

    # Wait for devices to arrive at initial positions
    wait_for_devices(devs)

    # Optionally, wait for stability if needed
    if accuracy is not None and time_stable is not None:
        wait_for_stability(positions_dict, accuracy, time_stable, timeout)

    # Add a grace period to allow for devices to settle
    sleep(1)

    # Emit 'scan_start_event'
    start_time = int(time.time())

    device_str = ", ".join([d.name for d in devs])
    det_str = ", ".join([f"{d.name}.finalvalue" for d in additional_devices])
    device_str = f"{device_str}, {det_str}" if det_str else device_str

    info_dict = {
        "devices": device_str,
        "fromdate": start_time,
        "info": scaninfo,
    }

    emit_scan_start_event(info_dict)

    try:
        for position in values:
            # Move devices to positions
            positions_dict = dict(zip(devs, position))
            move_devices_to_positions(positions_dict)

            # Wait for devices to arrive
            wait_for_devices(devs)

            # Optionally, wait for stability if needed
            if accuracy is not None and time_stable is not None:
                wait_for_stability(positions_dict, accuracy, time_stable, timeout)

            # Start detectors
            start_detectors(detlist, preset)

            # Wait for detectors to complete
            wait_for_detectors(detlist)

            # Wait for measurement to be done
            sleep(sleep_time)

    except Exception as e:
        session.log.error("Error during scan: %s", e)
    finally:
        # Emit 'scan_end_event'
        end_time = int(time.time() + 1)
        info_dict["todate"] = end_time
        emit_scan_end_event(info_dict)
