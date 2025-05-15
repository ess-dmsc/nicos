import numpy as np

from nicos.core import Attach, Moveable, Override, Param, Value, multiStatus, tupleof


def s_to_angle(s, E=5):
    return np.degrees(np.arcsin(2 * s / (E * np.sqrt(2))))


def angle_to_s(angle_deg, E=5):
    return 0.5 * E * np.sqrt(2) * np.sin(np.radians(angle_deg))


def cartesian_to_mover(cart, r=1.9964, E=5):
    sqrt2 = np.sqrt(2)
    D = np.array(
        [
            [0.5, 0.5, -r / 2, -0.25, -0.25],
            [-0.5, 0.5, r / 2, 0.25, -0.25],
            [0.5, 0.5, (1 - 2 * r) / 4, 0.25, 0.25],
            [-0.5, 0.5, (1 + 2 * r) / 4, -0.25, 0.25],
            [0.0, 1 / sqrt2, -1 / (2 * sqrt2), 0.0, 1 / (2 * sqrt2)],
        ]
    )
    return s_to_angle(D @ cart, E)


def mover_to_cartesian(angles_deg, r=1.9964, E=5):
    sqrt2 = np.sqrt(2)
    D = np.array(
        [
            [0.5, 0.5, -r / 2, -0.25, -0.25],
            [-0.5, 0.5, r / 2, 0.25, -0.25],
            [0.5, 0.5, (1 - 2 * r) / 4, 0.25, 0.25],
            [-0.5, 0.5, (1 + 2 * r) / 4, -0.25, 0.25],
            [0.0, 1 / sqrt2, -1 / (2 * sqrt2), 0.0, 1 / (2 * sqrt2)],
        ]
    )
    s = angle_to_s(np.asarray(angles_deg, dtype=float), E)
    return np.linalg.inv(D) @ s


class SeleneMover(Moveable):
    """
    Move y, z, Rx, Ry, Rz of the Selene guide carriage **as one logical axis**.
    """

    # Order must match the column order of matrix *D*
    motor_names = ("flreus", "prreds", "prlids", "prlius1", "prlius2")

    attached_devices = {name: Attach(name.upper(), Moveable) for name in motor_names}

    parameters = {
        "eccentricity": Param(
            "Eccentricity of pivot (mm)", type=float, default=5.0, settable=False
        ),
        "guide_ratio": Param(
            "Guide ratio h/w", type=float, default=1.9964, settable=False
        ),
    }

    parameter_overrides = {
        "fmtstr": Override(default="[.3f, %.3f, %.3f, %.3f, %.3f]"),
        "unit": Override(default="", mandatory=False, settable=True),
    }

    valuetype = tupleof(float, float, float, float, float)  # y, z, Rx, Ry, Rz

    def _s_to_angle(self, s, E=5):
        return np.degrees(np.arcsin(2 * s / (E * np.sqrt(2))))

    def _angle_to_s(self, angle_deg, E=5):
        return 0.5 * E * np.sqrt(2) * np.sin(np.radians(angle_deg))

    def _cartesian_to_mover(self, cart, r=1.9964, E=5):
        sqrt2 = np.sqrt(2)
        D = np.array(
            [
                [0.5, 0.5, -r / 2, -0.25, -0.25],
                [-0.5, 0.5, r / 2, 0.25, -0.25],
                [0.5, 0.5, (1 - 2 * r) / 4, 0.25, 0.25],
                [-0.5, 0.5, (1 + 2 * r) / 4, -0.25, 0.25],
                [0.0, 1 / sqrt2, -1 / (2 * sqrt2), 0.0, 1 / (2 * sqrt2)],
            ]
        )
        return self._s_to_angle(D @ cart, E)

    def _mover_to_cartesian(self, angles_deg, r=1.9964, E=5):
        sqrt2 = np.sqrt(2)
        D = np.array(
            [
                [0.5, 0.5, -r / 2, -0.25, -0.25],
                [-0.5, 0.5, r / 2, 0.25, -0.25],
                [0.5, 0.5, (1 - 2 * r) / 4, 0.25, 0.25],
                [-0.5, 0.5, (1 + 2 * r) / 4, -0.25, 0.25],
                [0.0, 1 / sqrt2, -1 / (2 * sqrt2), 0.0, 1 / (2 * sqrt2)],
            ]
        )
        s = self._angle_to_s(np.asarray(angles_deg, dtype=float), E)
        return np.linalg.inv(D) @ s

    def _angles(self, cart):
        return self._cartesian_to_mover(
            np.asarray(cart, dtype=float), r=self.guide_ratio, E=self.eccentricity
        )

    def _cartesian(self, angles):
        return self._mover_to_cartesian(
            np.asarray(angles, dtype=float), r=self.guide_ratio, E=self.eccentricity
        )

    def _extractPos(self, cart):
        return list(zip(self.motor_names, self._angles(cart)))

    def _readPos(self, maxage=0):
        ang = [self._adevs[n].read(maxage) for n in self.motor_names]
        return self._cartesian(ang)

    def _createPos(self, **kw):
        return np.array([kw[k] for k in ("y", "z", "Rx", "Ry", "Rz")], dtype=float)

    def doStart(self, target):
        for name, angle in zip(self.motor_names, self._angles(target)):
            self._adevs[name].start(angle)

    def doIsAllowed(self, target):
        for name, angle in zip(self.motor_names, self._angles(target)):
            ok, why = self._adevs[name].isAllowed(angle)
            if not ok:
                return False, why
        return True, ""

    def doRead(self, maxage=0):
        return self._readPos(maxage).tolist()

    def doStatus(self, maxage=0):
        return multiStatus(
            self._adevs,
            maxage=maxage,
        )

    # Nice-looking prompt in *status*:
    def valueInfo(self):
        return (
            Value("y", unit="mm", fmtstr="%.3f"),
            Value("z", unit="mm", fmtstr="%.3f"),
            Value("Rx", unit="mrad", fmtstr="%.3f"),
            Value("Ry", unit="mrad", fmtstr="%.3f"),
            Value("Rz", unit="mrad", fmtstr="%.3f"),
        )
