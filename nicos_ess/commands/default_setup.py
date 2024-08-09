from nicos import session
from nicos.commands import usercommand


@usercommand
def default_setup(*args):
    loaded_devices = {
        devname: dev_info
        for devname, dev_info in session.devices.items()
        if devname not in session._setup_info["system"]["devices"]
    }
    for devname in args:
        device = loaded_devices.get(devname)
        if device:
            device.device_default()  ## Implement device_default() for devices?
