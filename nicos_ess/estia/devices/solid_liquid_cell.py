from nicos.core import Attach, Moveable, Override, Readable
from nicos.devices.abstract import MappedMoveable


class SolidLiquidCell(Moveable):
    """
    Device for controlling a solid-liquid cell.
    """

    attached_devices = {
        "top_s1": Attach("Top side solenoid 1", MappedMoveable),
        "top_s2": Attach("Top side solenoid 2", MappedMoveable),
        "top_s3": Attach("Top side solenoid 3", MappedMoveable),
        "bottom_s1": Attach("Bottom side solenoid 1", MappedMoveable),
        "bottom_s2": Attach("Bottom side solenoid 2", MappedMoveable),
        "bottom_s3": Attach("Bottom side solenoid 3", MappedMoveable),
        "temperature": Attach("Temperature sensor", Readable),
    }

    parameter_overrides = {
        "unit": Override(mandatory=False, settable=False),
    }
