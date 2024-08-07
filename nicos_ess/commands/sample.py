from nicos import session
from nicos.commands import usercommand
from nicos_ess.devices.sample import EssSample


def _find_sample_dev():
    for dev in session.devices.values():
        if isinstance(dev, EssSample):
            return dev
    raise RuntimeError("Could not find Sample device")


def _dev_exists(device):
    return any(device == dev.name for dev in session.devices.values())


@usercommand
def set_sample_fields(**kwargs):
    sample_dev = _find_sample_dev()
    for field in kwargs:
        device = kwargs[field]
        if field is None or kwargs[field] is None:
            session.log.error("Field and/or device is None")
            return

        if hasattr(sample_dev, field) and _dev_exists(device):
            setattr(sample_dev, field, device)
            session.log.info(f"Sample.{field} set to '{device}'.")
        else:
            session.log.error(
                f"Device '{device}' and/or Sample.{field} does not exist."
            )


@usercommand
def clear_sample_fields(*args):
    sample_dev = _find_sample_dev()
    for field in args:
        if field is None:
            session.log.error("Field is None")
            return

        if hasattr(sample_dev, field):
            setattr(sample_dev, field, "")
            session.log.info(f"Sample.{field} cleared.")
        else:
            session.log.error(f"Field '{field}' does not exist for Sample device.")
