from nicos import session
from nicos.commands import usercommand


@usercommand
def default_setup(*args):
    loaded_devices = {
        devname: dev
        for devname, dev in session.devices.items()
        if devname not in session._setup_info["system"]["devices"]
    }
    for device in args:
        loaded_devices.get(
            device, lambda: None
        ).device_default()  ## Implement device_default() for devices?
