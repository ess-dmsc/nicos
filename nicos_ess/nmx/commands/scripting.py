from nicos.commands import usercommand
from nicos import session

__all__ = ["do_trans", "do_sans", "do_simultaneous", "nmx_pinhole_reset"]

PINHOLE_DEV_NAMES = [
    "pinhole__virtual_motor",
    "pinhole__carousel_rotation",
    "pinhole__carousel_electromagnet",
    "pinhole__carousel_v_raise",
    "pinhole__aperture_arm"
]


@usercommand
def do_trans(trans_duration=None, trans_duration_type=None):
    raise NotImplementedError("Please implement do_trans script")


@usercommand
def do_sans(sans_duration=None, sans_duration_type=None):
    raise NotImplementedError("Please implement do_sans script")


@usercommand
def do_simultaneous(sans_duration=None, sans_duration_type=None):
    raise NotImplementedError("Please implement do_simultanous script")


@usercommand
def nmx_pinhole_reset():
    """ Reset all pinhole motion devices in a single command."""
    for device_name in PINHOLE_DEV_NAMES:
        try:
            dev = session.getDevice(device_name)
        except Exception as e:
            print("ERROR: " + str(e))
            continue
        else:
            dev.reset()
            print(f"{device_name} was reset.")
    print("Finished pinhole reset!")

