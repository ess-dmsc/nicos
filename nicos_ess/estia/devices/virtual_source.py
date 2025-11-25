import numpy as np

from nicos.core import (
    Attach,
    Moveable,
    Override,
    Readable,
    Value,
    multiStatus,
    status,
    tupleof,
)


class VSCalculator(Readable):
    """Readout of the Virtual Slit Motions to find the
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

    def _findWidth(self, angle, gap):
        rad = np.deg2rad(angle)
        return 2 * gap * np.sin(rad)

    def _doReadPositions(self, maxage):
        gap, height = self._adevs["slit"].read(maxage)
        angle = self._adevs["rot"].read(maxage)
        width = self._findWidth(angle, gap)
        return width, height

    def doRead(self, maxage=0):
        return self._doReadPositions(maxage)

    def doStatus(self, maxage=0):
        return status.OK, ""

    def doSetPosition(self, pos):
        pass


class VirtualSlit(Moveable):
    """Device to control the motions of the ESTIA virtual slit to create
    a slit opening determined by input of blade gap, and desired width
    angle readout is in degrees"""

    parameter_overrides = {
        "fmtstr": Override(
            default="slit: [%.3f x %.3f]mm | angle: %.3fdeg | gap: %.3fmm"
        ),
        "unit": Override(default="", mandatory=False, settable=False),
    }
    valuetype = tupleof(float, float, float)

    devices = ["slit", "rot"]

    attached_devices = {
        "slit": Attach("the slit blades", Moveable),
        "rot": Attach("the rotation stage", Moveable),
    }

    def _findWidth(self, angle, gap):
        rad = np.deg2rad(angle)
        return 2 * gap * np.sin(rad)

    def _findAngle(self, width, gap):
        angle = np.arcsin(width / (2 * gap))
        return np.rad2deg(angle)

    def _parseTargets(self, target):
        # target = [slit width(y), blade gap(x), slit height(z)]
        slit_target = target[1:]
        angle = self._findAngle(target[0], target[1])
        return [slit_target, angle]

    def _doReadPositions(self, maxage):
        gap, height = self._adevs["slit"].read(maxage)
        angle = self._adevs["rot"].read(maxage)
        width = self._findWidth(angle, gap)
        return width, height, angle, gap

    def doStart(self, target):
        for name, pos in zip(self.devices, self._parseTargets(target)):
            self._adevs[name].start(pos)

    def doIsAllowed(self, target):
        for name, pos in zip(self.devices, self._parseTargets(target)):
            ok, why = self._adevs[name].isAllowed(pos)
            if not ok:
                return ok, f"{name} {why}"
        return ok, why

    def doRead(self, maxage=0):
        return self._doReadPositions(maxage)

    def doStatus(self, maxage=0):
        return multiStatus(self._adevs, maxage=maxage)

    def valueInfo(self):
        return (
            Value("Slit Width", unit="mm", fmtstr="%.3f"),
            Value("Blade Gap", unit="mm", fmtstr="%.3f"),
            Value("Slit Height", unit="mm", fmtstr="%.3f"),
        )
