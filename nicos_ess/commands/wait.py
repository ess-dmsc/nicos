import time

from nicos import session
from nicos.commands import helparglist, usercommand
from nicos.core import SIMULATION


@usercommand
@helparglist("device, target, accuracy, time_stable, [timeout]")
def waitfor_stable(device, target, accuracy, time_stable, timeout=3600):
    """Wait for the device to be within a certain range of the target value
    for a defined continuous number of seconds.

    If the device takes too long to stabilise then the action will timeout.

    Example:

    >>> waitfor_stable(dev1, 10, 1, 30, 600)

    will wait until the device position is between 9 and 11 for a continuous
    period of 30 seconds, but will exit after 10 minutes if
    stability is not reached.

    .. note::

       The default timeout is an hour (3600 s).
    """
    if session.mode == SIMULATION:
        session.clock.tick(time_stable)
        return
    dev = session.getDevice(device)
    start_time = int(time.monotonic())
    in_range = False
    start_in_range = None

    while True:
        curr_pos = dev.read()
        curr_time = int(time.monotonic())

        if curr_time > start_time + timeout:
            session.log.warning(
                "stablilisation timed out - %s might not be " "stable", device
            )
            break

        if abs(target - curr_pos) <= accuracy:
            if not in_range:
                in_range = True
                start_in_range = curr_time
                session.log.warning(
                    "%s is within range, waiting %s seconds " "for it to stabilise",
                    device,
                    time_stable,
                )
        else:
            if in_range:
                session.log.warning("%s is no longer in range", device)
            in_range = False

        if in_range and curr_time > start_in_range + time_stable:
            session.log.warning("%s is considered stable", device)
            break

        session.delay(dev._long_loop_delay)

@usercommand
@helparglist("chopper, frequency")
def maw_chopper(chopper, frequency):
    """Move a chopper to a new speed and wait until it reports being in phase.

    Sets the chopper's speed setpoint, starts it if required, and then
    waits for the chopper's phase status to leave and re-enter the
    'In phase' state before returning control.

    Example:
    >>> maw_chopper(mini_chopper, '7 Hz')
    will set mini_chopper's speed to 7 Hz, start it if it is not already
    running, and wait until it has phased and settled back into
    'In phase' before continuing.

    .. note::
       This command will block until the chopper reports 'In phase',
       which may take some time depending on the chopper's current speed
       and the requested target speed.
    """
    chopper_name = chopper.name
    session.devices[chopper_name + '_speed'].move(frequency)
    if chopper.read() == 2:
        session.devices[chopper_name + '_speed'].move('Start')
    session.devices[chopper_name + '_speed'].waitfor('!=\'In phase\'')
    session.devices[chopper_name + '_speed'].waitfor('==\'In phase\'')