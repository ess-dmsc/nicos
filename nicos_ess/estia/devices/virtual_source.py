from nicos.core import (
    Attach,
    Moveable,
    Override,
    Param,
    Value,
    dictof,
    multiStatus,
    oneof,
    tupleof,
)


class VirtualSource(Moveable):
    """Controller for the Virtual Source Slit System

    The slit consists of two L-shaped blades controlled by 5 motors:
    - 2 motions along the x-axis
    - 2 motions along the y-axis
    - 1 shared rotational motion along the z-axis

    Axis stated are defined via the right-hand rule with +x heading down the beamline towards the sample

    Device allows for control and reading of all 5 motor positions.
    """

    parameters = {
        "opmode": Param(
            "Mode of operation",
            type=oneof("4blades", "centered"),
            settable=True,
        ),
        "fmtstr_map": Param(
            "A dictionary mapping operation modes to format strings (used for "
            "internal management).",
            type=dictof(str, str),
            settable=False,
            mandatory=False,
            userparam=False,
            default={
                "4blades": "%.2f %.2f %.2f %.2f %.2f",
                "centered": "(%.2f mm x %.2f mm) %.2f deg",
            },
        ),
        "offsets": Param(
            "Change the offset(s) of the virtual source\n"
            "In order of: left, right, bottom, top, rotation",
            type=tupleof(float, float, float, float, float),
            settable=True,
            default=(0.0, 0.0, 0.0, 0.0, 0.0),
        ),
    }
    parameter_overrides = {
        "unit": Override(default="", mandatory=False, settable=True),
    }
    devices = ["slit", "rot"]

    attached_devices = {
        "slit": Attach("the slit blades", Moveable),
        "rot": Attach("the rotation stage", Moveable),
    }

    def doInit(self, mode):
        self.doWriteOffsets(self.offsets)

    def doWriteOffsets(self, offset):
        slitBlades = ["left", "right", "bottom", "top"]
        self._adevs["rot"]._setROParam("offset", offset[4])

        for blade, blade_offset in zip(slitBlades, offset[:-1]):
            self._adevs["slit"]._adevs[blade]._setROParam("offset", blade_offset)

    def _returnGap(self, pos):
        # [-left, +right, -bottom, +top]
        left, right, bottom, top = pos
        width = abs((left + right) / 2)
        height = abs((top + bottom) / 2)
        return [width, height]

    def _parseTargets(self, target):
        # angle target must be split from slit target since it is an independent attachment
        if self.opmode == "centered":
            return [target[:-1], target[2]]
        else:
            return [target[:-1], target[4]]

    def doStart(self, target):
        for name, pos in zip(self.devices, self._parseTargets(target)):
            self._adevs[name].start(pos)

    def doIsAllowed(self, target):
        for name, pos in zip(self.devices, self._parseTargets(target)):
            ok, why = self._adevs[name].isAllowed(pos)
            if not ok:
                return ok, f"{name} {why}. Commanded to {pos}"
        return ok, why

    def doRead(self, maxage=0):
        self._syncOpmode(self._adevs["slit"].opmode, self.opmode)
        positions = self._adevs["slit"]._doReadPositions(maxage)
        angle = self._adevs["rot"].read(maxage)

        if self.opmode == "centered":
            width, height = self._returnGap(positions)
            return [width, height, angle]
        left, right, bottom, top = positions
        return [left, right, bottom, top, angle]

    def doStatus(self, maxage=0):
        return multiStatus(self._adevs, maxage=maxage)

    def valueInfo(self):
        if self.opmode == "centered":
            return (
                Value("Slit Width", unit="mm", fmtstr="%.3f"),
                Value("Slit Height", unit="mm", fmtstr="%.3f"),
                Value("Angle", unit="deg", fmtstr="%.3f"),
            )
        else:
            return (
                Value("Left", unit="mm", fmtstr="%.3f"),
                Value("Right", unit="mm", fmtstr="%.3f"),
                Value("Bottom", unit="mm", fmtstr="%.3f"),
                Value("Top", unit="mm", fmtstr="%.3f"),
                Value("Angle", unit="deg", fmtstr="%.3f"),
            )

    def doUpdateOpmode(self, value):
        if value == "centered":
            self.valuetype = tupleof(float, float, float)
        else:
            self.valuetype = tupleof(float, float, float, float, float)

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
        # the general slit device is locked to the opmode of the virtual source device
        if slit_mode == vs_mode:
            return
        self._adevs["slit"]._setROParam("opmode", vs_mode)
