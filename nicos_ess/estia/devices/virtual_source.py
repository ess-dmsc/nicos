from nicos.core.errors import InvalidValueError
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
    anytype,
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
            type=oneof("4blades", "4blades_opposite", "centered", "offcentered"),
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
                "4blades": "%.2f, %.2f, %.2f, %.2f, %.2f",
                "4blades_opposite": "%.2f, %.2f, %.2f, %.2f, %.2f",
                "centered": "(%.2f mm x %.2f mm) %.2f deg",
                "offcentered": "(%.2f, %.2f) %.2f mm x %.2f mm, %.2f deg",
            },
        ),
        "userlimits": Param(
            "adjust settings of each motor limit. "
            "limits should be written in list form [min,max]",
            type=dictof(str, anytype),
            settable=True,
            userparam=False,
            default={},
        ),
    }
    parameter_overrides = {
        "unit": Override(default="", mandatory=False, settable=True),
    }
    devices = ["slit", "rot"]
    valuetype = (float, float, float, float, float)

    attached_devices = {
        "slit": Attach("the slit blades", Moveable),
        "rot": Attach("the rotation stage", Moveable),
    }

    def doPreinit(self, mode):
        adev_limits = {"left": [], "right": [], "bottom": [], "top": [], "rot": []}
        adevs = ("left", "right", "bottom", "top", "rot")

        for device in adevs:
            # slit parts are attached-attached devices
            if device != "rot":
                adev_limits[device] = self._adevs["slit"]._adevs[device].userlimits
            else:
                adev_limits[device] = self._adevs[device].userlimits

        self._setROParam("userlimits", adev_limits)

    def _parseTargets(self, target):
        # angle target must be split from slit target since it is an independent attachment
        if self.opmode == "centered":
            return [target[:-1], target[2]]
        else:
            return [target[:-1], target[4]]

    def doStart(self, target):
        print(f"{self._parseTargets(target)}")
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

        # [-left, +right, -bottom, +top]
        left, right, bottom, top = positions

        if self.opmode == "centered":
            width = right - left
            height = top - bottom

            return [width, height, angle]
        if self.opmode == "offcentered":
            centerx = abs((left + right) / 2)
            centery = abs((top + bottom) / 2)
            width = right - left
            height = top - bottom

            return [centerx, centery, width, height, angle]
        else:
            if self.opmode == "4blades_opposite":
                left *= -1
                bottom *= -1
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
        if self.opmode == "offcentered":
            return (
                Value("Center-x", unit="mm", fmtstr="%.3f"),
                Value("Center-y", unit="mm", fmtstr="%.3f"),
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

    def doUpdateUserlimits(self, values):
        # device order: left, right, bottom, top, rotation (rot)

        # Check if limit set is valid
        # Bad limist are not set regardless, but without this no error is raised
        adev_abslimits = 0
        for adev_name in values:
            if values[adev_name] == [] or values[adev_name] == ():
                raise InvalidValueError(
                    self,
                    f"userlimits for {adev_name} is empty, please set the limits"
                    "in the format [min,max] or (min,max)",
                )
            # verify that min < max
            if values[adev_name][0] > values[adev_name][1]:
                raise InvalidValueError(
                    self, f"min limit is greater than max limit for {adev_name}!"
                )
            # verify that we are not going over the abslimits
            if adev_name != "rot":
                adev_abslimits = self._adevs["slit"]._adevs[adev_name].abslimits
            else:
                adev_abslimits = self._adevs["rot"].abslimits

            if values[adev_name][0] < adev_abslimits[0]:
                raise InvalidValueError(
                    self,
                    f"userlimits for {adev_name} is lower than abslimits {adev_abslimits}!",
                )
            elif values[adev_name][1] > adev_abslimits[1]:
                raise InvalidValueError(
                    self,
                    f"userlimits for {adev_name} is greater than abslimits {adev_abslimits}!",
                )
        # set the new limits
        for adev_name in values:
            if adev_name != "rot":
                self._adevs["slit"]._adevs[adev_name]._setROParam(
                    "userlimits", values[adev_name]
                )
            else:
                self._adevs["rot"]._setROParam("userlimits", values[adev_name])
