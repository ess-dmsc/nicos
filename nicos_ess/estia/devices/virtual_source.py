import numpy as np

from nicos.core import (
    Attach,
    Moveable,
    Override,
    Param,
    Readable,
    Value,
    dictof,
    multiStatus,
    oneof,
    status,
    tupleof,
)


class VSCalculator(Readable):
    """Readout Calculator for the Virtual Source Slit System

    The slit consists of two L-shaped blades controlled by 5 motors:
    - 2 motions along the x-axis
    - 2 motions along the y-axis
    - 1 shared rotational motion along the z-axis

    Axis stated are defined via the right-hand rule with +x heading down the beamline towards the sample

    The vertical height of the slit is determined by standard slit motions, however
    the width is determined by the gap distance between the blades along the x-axis
    and then a shared rotation around the z-axis.
    """

    parameters = {
        "fmtstr_map": Param(
            "A dictionary mapping operation modes to format strings (used for internal management).",
            type=dictof(str, str),
            settable=False,
            mandatory=False,
            userparam=False,
            default={
                "4blades": "(%.3f mm x %.3f mm) %.3f deg",
                "centered": "(%.3f mm x %.3f mm) %.3f deg",
            },
        ),
        "opmode": Param(
            "Mode of operation",
            type=oneof("4blades", "centered"),
            settable=True,
            default="4blades",
        ),
    }

    parameter_overrides = {
        "unit": Override(default="", mandatory=False, settable=True),
    }
    valuetype = tupleof(float, float)

    attached_devices = {
        "slit": Attach("the slit blades", Moveable),
        "rot": Attach("the rotation stage", Moveable),
    }

    def _findGap(self, pos, angle):
        # [-left, +right, -bottom, +top]
        l, r, b, t = pos
        height = t - b

        rad = np.deg2rad(angle)

        left_gap = float(-(l * np.sin(rad)))
        right_gap = float(r * np.sin(rad))
        width = left_gap + right_gap

        return [width, height]

    def _doReadPositions(self, maxage):
        positions = self._adevs["slit"]._doReadPositions(maxage)
        angle = self._adevs["rot"].read(maxage)

        width, height = self._findGap(positions, angle)
        return [width, height, angle]

    def doRead(self, maxage=0):
        # reader opmode should take prioriy over slit opmode
        self._syncOpmode(self._adevs["slit"].opmode, self.opmode)
        return self._doReadPositions(maxage)

    def doStatus(self, maxage=0):
        return status.OK, f"{self.opmode} mode"

    def doSetPosition(self, pos):
        pass

    def doWriteFmtstr(self, value):
        # since self.fmtstr_map is a readonly dict a temp. copy is created
        # to update the dict and then put to cache back
        tmp = dict(self.fmtstr_map)
        tmp[self.opmode] = value
        self._setROParam("fmtstr_map", tmp)

    def doReadFmtstr(self):
        return self.fmtstr_map[self.opmode]

    def doWriteOpmode(self, value):
        if self._cache:
            self._cache.invalidate(self, "value")
            self._cache.put(self, "fmtstr", self.fmtstr_map[value])

    def _syncOpmode(self, slit_mode, vs_mode):
        if slit_mode == vs_mode:
            return
        self._adevs["slit"]._setROParam("opmode", vs_mode)


class VirtualSlit(Moveable):
    parameter_overrides = {
        "fmtstr": Override(
            default={
                "slit: [%.3f x %.3f]mm | angle: %.3fdeg | gap: %.3fmm",
            }
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
        # target = [slit width, blade gap, slit height]
        slit_target = target[1:]
        angle = self._findAngle(target[0], target[1])
        return [slit_target, angle]

    def _doReadPositions(self, maxage):
        gap, height = self._adevs["slit"].read(maxage)
        angle = self._adevs["rot"].read(maxage)
        width = self._findWidth(angle, gap)
        return [width, height, angle, gap]

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
