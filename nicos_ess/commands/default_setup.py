from nicos import session
from nicos.commands import usercommand


@usercommand
def default_setup():
    system_devs = (
        session.configured_devices if "system" in session.loaded_setups else {}
    )

    for devname, dev in session.devices.items():
        if devname not in system_devs:
            session.log.info(dev)
