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
def nmx_pinhole_reset():
    """ Reset all NMX pinhole motion devices in a single command."""
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

