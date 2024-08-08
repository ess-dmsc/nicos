from nicos import session
from nicos.commands import usercommand


@usercommand
def default_setup():
    system_devs = (
        session.configured_devices if "system" in session.loaded_setups else {}
    )

    for devname, dev in session.devices.items():
        session.log.info(f"configured devices: {system_devs}")
        if devname not in system_devs:
            session.log.info(f"non system dev: {dev}")
        session.log.info(f"system dev: {dev}")
