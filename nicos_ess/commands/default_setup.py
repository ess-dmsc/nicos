from nicos import session
from nicos.commands import usercommand


@usercommand
def default_setup():
    system_devs = (
        session.configured_devices if "system" in session.loaded_setups else {}
    )

    session.log.info(f"loaded setups: {session.loaded_setups}")
    session.log.info(f"setup info: {session._setup_info}")

    for devname, dev in session.devices.items():
        if devname not in system_devs:
            session.log.info(f"non system dev: {dev}")
        session.log.info(f"system dev: {dev}")
