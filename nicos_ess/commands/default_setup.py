from nicos import session
from nicos.commands import usercommand


@usercommand
def default_setup():
    system_devs = session._setup_info["system"]["devices"]

    loaded_devices = {}
    for devname, dev in session.devices.items():
        if devname not in system_devs:
            loaded_devices[devname] = dev

    session.log.info(loaded_devices)
