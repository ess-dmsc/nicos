from nicos.core import Moveable, Attach, Override
from nicos.devices.epics.pva import EpicsReadable, EpicsMappedMoveable


class SolidLiquidCell(Moveable):
    """
    Device for controlling a solid-liquid cell.
    """

    attached_devices = {
        "top_s1": Attach("Top side solenoid 1", EpicsMappedMoveable),
        "top_s2": Attach("Top side solenoid 2", EpicsMappedMoveable),
        "top_s3": Attach("Top side solenoid 3", EpicsMappedMoveable),
        "bottom_s1": Attach("Bottom side solenoid 1", EpicsMappedMoveable),
        "bottom_s2": Attach("Bottom side solenoid 2", EpicsMappedMoveable),
        "bottom_s3": Attach("Bottom side solenoid 3", EpicsMappedMoveable),
        "temperature": Attach("Temperature sensor", EpicsReadable),
    }

    parameter_overrides = {
        "unit": Override(mandatory=False, settable=False),
    }
