from nicos import session
from nicos.commands import usercommand
from nicos_ess.devices.scichat import ScichatBot

__all__ = ["scichat_send"]


def _find_scichat_dev():
    for dev in session.devices.values():
        # Should only be one at most
        if isinstance(dev, ScichatBot):
            return dev
    raise RuntimeError("Could not find ScichatBot device")


@usercommand
def scichat_send(message):
    try:
        _find_scichat_dev().send(message)
    except RuntimeError as error:
        # Log it but don't propagate as we don't want it to stop a script
        session.log.warn(f"could not send message to SciChat: {error}")
