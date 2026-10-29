from nicos.commands import usercommand
from nicos.commands.device import reference

__all__ = ["home"]


@usercommand
def home(dev):
    """Home the device if possible. This is equal to performing a reference
    drive of the device.

    >>> home(phi)
    """
    reference(dev)
