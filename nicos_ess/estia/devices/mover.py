import numpy as np

from nicos.core import Attach, Moveable, Override, Param, Value, multiStatus, tupleof

MOVER_LENGTH_SG1 = 2750
MOVER_LENGTH_SG2 = 3600
BEAM_HEIGHT_SG1 = 1088
BEAM_HEIGHT_SG2 = 1098


class SeleneMover(Moveable):
    """
    Move y, z, Rx, Ry, Rz of the Selene guide carriage **as one logical axis**.
    """

    # Order must match the column order of matrix *D*
    motor_names = ("s1", "s2", "s3", "s4", "s5")

    attached_devices = {name: Attach(name.upper(), Moveable) for name in motor_names}

    parameters = {
        "eccentricity": Param(
            "Eccentricity of pivot (mm)", type=float, default=5.0, settable=False
        ),
        "guide_ratio": Param(
            "Guide ratio h/w", type=float, default=1.9964, settable=False
        ),
        "mover_width": Param(
            "distance between mover feet, w", type=float, default=550, settable=False
        ),
        "mover_length": Param(
            "Length distance between mover feet, for a selene guide",
            type=float,
            default=MOVER_LENGTH_SG1,
            settable=True,
        ),
        "beam_height": Param(
            "Height of the beam above the mover plane for a selene guide",
            type=float,
            default=BEAM_HEIGHT_SG1,
            settable=True,
        ),
    }

    parameter_overrides = {
        "fmtstr": Override(default="[%.3f, %.3f, %.3f, %.3f, %.3f]"),
        "unit": Override(default="", mandatory=False, settable=True),
    }

    valuetype = tupleof(float, float, float, float, float)  # y, z, Rx, Ry, Rz

    def _s_to_angle(self, s):
        return np.degrees(np.arcsin(2 * s / (self.eccentricity * np.sqrt(2)))) + 180

    def _angle_to_s(self, angle_deg):
        return 0.5 * self.eccentricity * np.sqrt(2) * np.sin(np.radians(angle_deg))

    def SG_from_params(self):
        """Get SG used based on mover_length and beam_height"""
        SG_params = {
            "SG1": [MOVER_LENGTH_SG1, BEAM_HEIGHT_SG1],
            "SG2": [MOVER_LENGTH_SG2, BEAM_HEIGHT_SG2],
        }
        for sg in SG_params:
            if SG_params[sg] == [self.mover_length, self.beam_height]:
                return sg

    def get_r(self):
        return self.beam_height / self.mover_width

    def get_A(self):
        A_SG1 = np.array(
            [
                [0, 1, -1, 0, 0],
                [0, 0, 0, 1, -1],
                [0, 1, 1, 0, 0],
                [0, 0, 0, 1, 1],
                [np.sqrt(2), 0, 0, 0, 0],
            ]
        )

        A_SG2 = np.array(
            [
                [0, 1, -1, 0, 0],
                [0, 0, 0, -1, 1],
                [0, 1, 1, 0, 0],
                [0, 0, 0, 1, 1],
                [np.sqrt(2), 0, 0, 0, 0],
            ]
        )

        if self.SG_from_params() == "SG1":
            return A_SG1
        elif self.SG_from_params() == "SG2":
            return A_SG2

    def _mover_to_cartesian(self, angles):
        """
        Takes in an array of angles from the mover feet motors (either selene guide 1 or 2)
        and converts the angles into an array of [y, z, Rx, Ry, Rz]
        This follows the naming convention of the mover feet documentation
        for the matrix names and Cartesian axes (z is vertical against gravity and y
        is across the beam, the R's are rotations around the corresponding axis.

        Returns:  np.ndarray [y, z, Rx, Ry, Rz]
        """
        r = self.get_r()
        A = self.get_A()

        B = np.array(
            [
                [0, 0, r, 0, 0],
                [0, 0, r, 0, 0],
                [0, 0, 0, 0, 0],
                [0, 0, 0, 0, 0],
                [0, 0, 0, 0, 0],
            ]
        )

        M = np.array(
            [
                [1 / 2, 1 / 2, 0, 0, 0],
                [0, 0, 1 / 2, 1 / 4, 1 / 4],
                [0, 0, 0, 1, -1],
                [0, 0, -1, 1 / 2, 1 / 2],
                [1, -1, 0, 0, 0],
            ]
        )

        # calculation of motor positions
        # conversion of angle to displacement as per documentation

        D_inv = np.linalg.inv(np.linalg.inv(M @ A) @ (np.identity(5) - M @ B))
        S = self._angle_to_s(angles - 180)
        X = D_inv @ S

        X[2] = np.degrees(np.arcsin(X[2] / self.mover_width))
        X[3] = np.degrees(np.arcsin(X[3] / self.mover_length))
        X[4] = np.degrees(np.arcsin(X[4] / self.mover_length))

        return X

    def _cartesian_to_mover(self, cart):
        """
        Takes in a cart (either selene guide 1 or 2) and converts the desired y, z,
        or rotation into a movement in angle for each mover foot motor.
        This follows the naming convention of the mover feet documentation
        for the matrix names.

        Returns: np.ndarray of 5 angles for each of the 5 motors on the feet
        """
        r = self.get_r()
        A = self.get_A()

        B = np.array(
            [
                [0, 0, r, 0, 0],
                [0, 0, r, 0, 0],
                [0, 0, 0, 0, 0],
                [0, 0, 0, 0, 0],
                [0, 0, 0, 0, 0],
            ]
        )

        M = np.array(
            [
                [1 / 2, 1 / 2, 0, 0, 0],
                [0, 0, 1 / 2, 1 / 4, 1 / 4],
                [0, 0, 0, 1, -1],
                [0, 0, -1, 1 / 2, 1 / 2],
                [1, -1, 0, 0, 0],
            ]
        )

        # calculation of motor positions
        # conversion of angle to displacement as per documentation
        rho = self.mover_width * np.sin(np.radians(cart[2]))
        phi = self.mover_length * np.sin(np.radians(cart[3]))
        omega = self.mover_length * np.sin(np.radians(cart[4]))

        D = np.linalg.inv(M @ A) @ (np.identity(5) - M @ B)
        X = np.array([cart[0], cart[1], rho, phi, omega])
        S = D @ X

        angles_to_rotate = self._s_to_angle(S)
        return angles_to_rotate

    def _angles(self, cart):
        return self._cartesian_to_mover(
            np.asarray(cart, dtype=float), r=self.get_r(), E=self.eccentricity
        )

    def _cartesian(self, angles, cart):
        return self._mover_to_cartesian(
            np.asarray(angles, dtype=float), r=self.get_r(), E=self.eccentricity
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
