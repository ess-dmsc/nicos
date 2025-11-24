import numpy as np

from nicos.core import (
    Attach,
    Moveable,
    Override,
    Param,
    Readable,
    Value,
    floatrange,
    multiStatus,
    oneof,
    status,
    tupleof,
)


class VSCalculator(Readable):
    """Readout of the Virtual Slit Motions to calculate the
    width and height of the slit opening"""

    parameter_overrides = {
        "fmtstr": Override(default="%.3f x %.3f"),
        "unit": Override(default="mm", mandatory=False, settable=True),
    }
    valuetype = tupleof(float, float)

    attached_devices = {
        "slit": Attach("the slit blades", Moveable),
        "rot": Attach("the rotation stage", Moveable),
    }

    def _calculateWidth(self, gap, degree):
        rad = np.deg2rad(degree)
        return 2 * gap * np.sin(rad)

    def _doReadPositions(self, maxage):
        # [0] = "gap between the blades in x-direction" [1] = slit height
        gap, height = self._adevs["slit"].read(maxage)
        degree = self._adevs["rot"].read(maxage)
        width = self._calculateWidth(gap, degree)
        return width, height

    def doRead(self, maxage=0):
        positions = self._doReadPositions(maxage)
        width, height = positions
        return [width, height]

    def doStatus(self, maxage=0):
        return status.OK, ""

    def doSetPosition(self, pos):
        pass


class VirtualSlit(Moveable):
    """Device to control the motions of the ESTIA virtual slit to create
    a slit opening"""

    parameter_overrides = {
        "fmtstr": Override(default="slit: [%.3f x %.3f]mm\nangle: %.3f"),
        "unit": Override(default="", mandatory=False, settable=True),
    }
    valuetype = tupleof(float, float, float)
    dimensions = ["width", "height", "gap"]

    attached_devices = {
        "slit": Attach("the slit blades", Moveable),
        "rot": Attach("the rotation stage", Moveable),
    }

    def _calculateWidth(self, gap, degree):
        rad = np.deg2rad(degree)
        return 2 * gap * np.sin(rad)

    def _calculateAngle(self, width, gap):
        angle = np.arcsin(width / (2 * gap))
        return np.rad2deg(angle)

    def _doReadPositions(self, maxage):
        # [0] = "gap between the blades in x-direction" [1] = slit height
        gap, height = self._adevs["slit"].read(maxage)
        degree = self._adevs["rot"].read(maxage)
        width = self._calculateWidth(gap, degree)
        angle = self._calculateAngle(width, gap)
        return width, height, angle

    def doRead(self, maxage=0):
        return self._doReadPositions(maxage)

    def doStatus(self, maxage=0):
        return multiStatus(self._adevs, maxage=maxage)

    def valueInfo(self):
        return (
            Value("Width", unit="mm", fmtstr="%.3f"),
            Value("Height", unit="mm", fmtstr="%.3f"),
            Value("Blade Gap", unit="deg", fmtstr="%.3f"),
        )
