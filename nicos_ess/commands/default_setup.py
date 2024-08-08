from nicos import session
from nicos.commands import usercommand


@usercommand
def default_setup():
    for dev in session.devices.values():
        print(dev)
