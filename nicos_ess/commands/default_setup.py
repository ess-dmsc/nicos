from nicos import session
from nicos.commands import usercommand


@usercommand
def default_setup():
    system_devs = session._setup_info["system"]["devices"]
    loaded_devices = {
        dev if devname not in system_devs else {}
        for devname, dev in session.devices.items()
    }
    session.log.info(loaded_devices)
    """for devname, dev in session.devices.items():
        if devname not in system_devs:
            session.log.info(f"non system dev: {dev}")
        session.log.info(f"system dev: {dev}")"""
