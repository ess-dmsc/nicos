# *****************************************************************************
# NICOS, the Networked Instrument Control System of the MLZ
# Copyright (c) 2009-2024 by the NICOS contributors (see AUTHORS)
#
# This program is free software; you can redistribute it and/or modify it under
# the terms of the GNU General Public License as published by the Free Software
# Foundation; either version 2 of the License, or (at your option) any later
# version.
#
# This program is distributed in the hope that it will be useful, but WITHOUT
# ANY WARRANTY; without even the implied warranty of MERCHANTABILITY or FITNESS
# FOR A PARTICULAR PURPOSE.  See the GNU General Public License for more
# details.
#
# You should have received a copy of the GNU General Public License along with
# this program; if not, write to the Free Software Foundation, Inc.,
# 59 Temple Place, Suite 330, Boston, MA  02111-1307  USA
#
# Module authors:
#   Michele Brambilla <michele.brambilla@psi.ch>
#   Artur Glavic <artur.glavic@psi.ch
#
# *****************************************************************************


"""
This module implements the selene guides system. Guides can be properly
shaped using a number of screws on the back. A robot position and drives the
screwdriver.
"""

import numpy as np

from nicos.core import (
    Attach,
    MASTER,
    ModeError,
    Param,
    status,
    Value,
    oneof,
    dictof,
    tupleof,
    MoveError,
    SIMULATION,
)
from nicos.core.device import Moveable
from nicos.devices.generic import LockedDevice, BaseSequencer
from nicos.devices.generic.sequence import SeqDev, SeqMethod, SeqWait
from nicos_ess.devices.epics.pva.motor import EpicsMotor
from nicos.devices.epics.pva.epics_devices import EpicsMappedReadable
import yaml

from nicos_ess.estia.devices.multiline import MultilineController, MultilineChannel
from nicos_ess.estia.devices.selene_calculations import SeleneCalculator


class SeleneRobot(Moveable):
    parameters = {
        "adjuster_backslash": Param(
            "Backslash for rotation",
            mandatory=False,
            userparam=True,
            default=10.0,
            unit="deg",
        ),
        "adjuster_play": Param(
            "Typical play within screw",
            mandatory=False,
            userparam=True,
            default=5.0,
            unit="deg",
        ),
        "cart_backslash": Param(
            "Backslash for rotation",
            mandatory=False,
            userparam=True,
            default=0.2,
            unit="mm",
        ),
        "delta12": Param(
            "Distance between driver 1 and 2",
            mandatory=True,
            userparam=True,
            unit="mm",
        ),
        "engaged": Param(
            "Screwdriver engaged position",
            type=float,
            mandatory=True,
            userparam=False,
            unit="mm",
        ),
        "retracted": Param(
            "Screwdriver retracted position",
            type=float,
            mandatory=True,
            userparam=False,
            unit="mm",
        ),
        "position_data": Param(
            "YAML file that contins the positioning data",
            type=str,
            mandatory=True,
            userparam=False,
            unit="mm",
        ),
        "rotation": Param(
            "Rotation angle of selected driver0",
            type=float,
            mandatory=False,
            userparam=True,
            unit="deg",
        ),
        "driver": Param(
            "Selected screw driver (1/2)",
            type=oneof(0, 1, 2),
            default=1,
            settable=True,
            internal=True,
            unit="",
        ),
        "positions": Param(
            "Internal screw position tracking",
            type=dictof(int, dictof(int, tupleof(float, float))),
            default={},
            settable=True,
            internal=True,
            unit="",
        ),
        "rotations": Param(
            "Internal screw position tracking",
            type=dictof(int, dictof(int, float)),
            settable=True,
            internal=True,
            unit="",
        ),
        "current_position": Param(
            "Internal screw position tracking",
            type=tupleof(int, int),
            settable=True,
            internal=True,
            unit="",
        ),
        "vertical_screws": Param(
            "List of screw indices that adjust vertical mirrors",
            type=tupleof(int, int, int),
            default=(3, 5, 6),
            settable=False,
            userparam=False,
            unit="",
        ),
        "vertical_ratio": Param(
            "Ratio of mirror offset (mm) to adjuster rotation (deg)",
            type=float,
            default=360.0 / 0.09,
            settable=True,
            userparam=True,
            unit="deg/mm",
        ),
        "horizontal_ratio": Param(
            "Ratio of mirror offset (mm) to adjuster rotation (deg)",
            type=float,
            default=360.0 / 0.21,
            settable=True,
            userparam=True,
            unit="deg/mm",
        ),
    }

    attached_devices = {
        "move_x": Attach("Device for rotation", EpicsMotor),
        "move_z": Attach("Device for approache", EpicsMotor),
        "adjust1": Attach("Device for rotation", EpicsMotor),
        "approach1": Attach("Device for approache", EpicsMotor),
        "hex_state1": Attach("Device reporting the hex status", EpicsMappedReadable),
        "adjust2": Attach("Device for rotation", EpicsMotor),
        "approach2": Attach("Device for approache", EpicsMotor),
        "hex_state2": Attach("Device reporting the hex status", EpicsMappedReadable),
    }

    def doInit(self, mode):
        self._xpos_zero1 = 0.0
        self._xpos_zero2 = 0.0
        self._item_zpos = {}
        self._confirmed = {}
        self.calculate_zeros()
        if mode == MASTER:
            self.read(maxage=0)
        self._cache.addCallback(self._attached_adjust1, "value", self._update_rotation)
        self._cache.addCallback(self._attached_adjust2, "value", self._update_rotation)
        self._cache.addCallback(
            self._attached_approach1, "value", self._on_status_change_external
        )
        self._cache.addCallback(
            self._attached_approach2, "value", self._on_status_change_external
        )
        self._cache.addCallback(
            self._attached_move_x, "value", self._on_status_change_external
        )
        self._cache.addCallback(
            self._attached_move_z, "value", self._on_status_change_external
        )

    def shutdown(self):
        self._cache.removeCallback(
            self._attached_adjust1, "value", self._update_rotation
        )
        self._cache.removeCallback(
            self._attached_adjust2, "value", self._update_rotation
        )
        self._cache.removeCallback(
            self._attached_approach1, "value", self._on_status_change_external
        )
        self._cache.removeCallback(
            self._attached_approach2, "value", self._on_status_change_external
        )
        self._cache.removeCallback(
            self._attached_move_x, "value", self._on_status_change_external
        )
        self._cache.removeCallback(
            self._attached_move_z, "value", self._on_status_change_external
        )
        Moveable.shutdown(self)

    def calculate_zeros(self):
        if self.positions == {}:
            return
        items1 = 0
        items2 = 0
        for item, ditem in self.positions.items():
            data = np.array(list(ditem.values()), dtype=float)
            if item < 4:
                items2 += 1
                self._xpos_zero2 += (data[:, 0] % 480).mean()
            else:
                items1 += 1
                self._xpos_zero1 += (data[:, 0] % 480).mean()

            self._item_zpos[item] = data[:, 1].mean()

            self._confirmed[item] = {}
            for group in ditem.keys():
                self._confirmed[item][group] = False
        self._xpos_zero1 /= items1
        self._xpos_zero2 /= items2

    def _get_driver(self, xpos):
        # Return which driver is best suited for a certain x-position of the cart
        if abs(xpos % 480 - self._xpos_zero1) > abs(xpos % 480 - self._xpos_zero2):
            return 2
        else:
            return 1

    def _select_driver(self, driver=None):
        # use x-position to find the right screw driver to use
        xpos = self._attached_move_x.read()

        if driver is None:
            driver = self._get_driver(xpos)

        if driver in [1, 2]:
            self.log.debug("Configuring driver %i" % driver)
            self.driver = driver
        else:
            self.log.warning("Not valid for choose of driver %s" % driver)
            self.driver = 0

    @property
    def _adjust(self):
        if self.driver == 1:
            return self._attached_adjust1
        elif self.driver == 2:
            return self._attached_adjust2
        else:
            raise ValueError("No valid screw driver selected")

    @property
    def _approach(self):
        if self.driver == 1:
            return self._attached_approach1
        elif self.driver == 2:
            return self._attached_approach2
        else:
            raise ValueError("No valid screw driver selected")

    @property
    def _hex_state(self):
        if self.driver == 1:
            return self._attached_hex_state1
        elif self.driver == 2:
            return self._attached_hex_state2
        else:
            raise ValueError("No valid screw driver selected")

    def _engage(self):
        self.log.debug("Engaing driver")
        self._select_driver()
        self._adjust.wait()  # make sure the driver is not rotating while moving stage
        self._approach.maw(self.engaged)

    def _disengage(self):
        self.log.debug("Retracting driver")
        self._adjust.wait()  # make sure the driver is not rotating while moving stage
        self._attached_approach1.move(self.retracted)
        self._attached_approach2.maw(self.retracted)
        self._attached_approach1.wait()

    def engage(self):
        """
        User version to engage a screw if already positioned.
        Has some additional checkes and usability improvements.
        """
        self.doRead()
        if self.current_position == (-1, -1):
            self.log.error("Robot position does not fit any configuration, aborting")
            return
        xpos = self._attached_move_x.read()
        zpos = self._attached_move_z.read()
        xref, zref = self.positions[self.current_position[0]][self.current_position[1]]
        if abs(xpos - xref) > 0.5 or abs(zpos - zref) > 0.5:
            self.log.error("Robot position too far from configuration value, aborting")
            return
        if self._hex_state() in ["HexScrewInTransition", "HexScrewFullyOut"]:
            self._engage()
        if self._hex_state() != "HexScrewInserted":
            # issue with insertion
            self.log.warning("Screw driver not inserted correctly, trying to rotate")
            angle = self.rotations[self.current_position[0]][self.current_position[1]]
            self._adjust.maw(angle - 60)
            self._adjust.maw(angle + self.adjuster_play / 2.0)
            self._adjust.maw(angle)
            if self._hex_state() != "HexScrewInserted":
                self.log.error("Screw driver still not inserted correctly, aborting")
                self._disengage()
                return
        self.log.info("Driver in position")

    def disengage(self):
        """
        User version to disengage a screw driver.
        Makes sure it is not accidentally retracted without storing rotation position.
        """
        if self._hex_state() != "HexScrewInserted":
            self.log.info("Not engaged")
            return
        if abs(
            self.rotations[self.current_position[0]][self.current_position[1]]
            - self._adjust()
        ) > (self.adjuster_play / 2.0):
            self.log.error(
                "Rotation position does not fit the stored value, did you use adjust for last movement?"
            )
            return
        self._disengage()
        self.log.info("Driver retracted")

    def doRead(self, maxage=0):
        xpos = self._attached_move_x.read()
        zpos = self._attached_move_z.read()
        for item, ditem in self.positions.items():
            for group, dgroup in ditem.items():
                if abs(dgroup[0] - xpos) < 5.0 and abs(dgroup[1] - zpos) < 5.0:
                    try:
                        self.current_position = (item, group)
                    except ModeError:
                        return self.current_position
                    return (item, group)
        self.current_position = (-1, -1)
        return (-1, -1)

    def valueInfo(self):
        return (Value("Item", unit=""), Value("Group", unit=""))

    def doStart(self, position):
        if len(position) == 2:
            item, group = position
            driver = None
        elif len(position) == 3 and position[2] in [1, 2]:
            item, group, driver = position
        else:
            raise ValueError(
                "Position should be tuple (item, group) or (item, group, driver)"
            )

        x, z = self.positions[position[0]][position[1]]
        nominal_driver = self._get_driver(x)
        if driver:
            if nominal_driver != driver:
                # the user selected a driver that is not configured for this position
                self.log.debug(
                    "Manual overwrite of driver, changing expected x position"
                )
                if nominal_driver == 1:
                    x += self.delta12
                else:
                    x -= self.delta12
        else:
            driver = nominal_driver
        self.driver = driver
        self.log.debug(
            "Selected driver = %s, moving to (%i,%i) at location (%.2f, %.2f)"
            % (driver, position[0], position[1], x, z)
        )

        self._disengage()
        self._attached_move_x.move(x)
        self._attached_move_z.move(z)
        # move driver to last rotation, taking into account that full rotations don't matter
        rot = self.rotations[position[0]].get(position[1], 0.0)
        cur_rot = self._adjust()
        rot_diff = round((rot - cur_rot) / 360.0)
        adj_rot = cur_rot + 360 * rot_diff
        self._adjust.doAdjust(cur_rot, adj_rot)
        # adjusting offset changes user limits so we reset full range
        # TODO: fix the fucking userlimits for device without range!
        self._adjust.userlimits = (-100000, 100000)
        self._adjust.move(rot)

    # TODO: Implement an intelligent doStop to prevent any hardware issues and loss of rotation info

    def doTime(self, old_value, target):
        # estimate the approximate movement time from horizontal difference
        out = 30.0
        diff = abs(old_value[1] - target[1]) * 480.0
        tdiff = diff / self._attached_move_x.speed
        return out + tdiff

    def doReadRotation(self):
        try:
            return self._adjust()
        except AttributeError:
            return 0.0

    def doWriteRotation(self, value):
        self.adjust(value)

    def _update_rotation(self, key, value, time):
        self._pollParam("rotation")
        self._cache.invalidate(self, "status")

    def _on_status_change_external(self, key, value, time):
        self._cache.invalidate(self, "status")

    def doStatus(self, maxage=0):
        sout = status.OK
        motor_messages = []
        for motor in [
            self._attached_move_x,
            self._attached_move_z,
            self._attached_approach1,
            self._attached_approach2,
            self._attached_adjust1,
            self._attached_adjust2,
        ]:
            sout = max(sout, motor.status()[0])
            if (
                motor.status()[0] not in [status.OK, status.BUSY]
                and motor.status()[1].strip() != ""
            ):
                motor_messages.append(motor.status()[1])

        smessage = ""
        if sout == status.OK:
            if self._hex_state() == "HexScrewInserted":
                smessage += "ready  "
            elif self._hex_state() == "HexScrewFullyOut":
                smessage += "out     "
            elif self._hex_state() == "HexScrewMissed":
                return (status.ERROR, "screw missed")
            elif self._hex_state() == "HexScrewCollided":
                return (status.WARN, "driver collided")
        elif sout == status.BUSY:
            smessage += "driving "
        else:
            smessage += "        "

        if self.driver in [1, 2]:
            smessage += "D%i: %.1f°" % (self.driver, self._adjust())
        if len(motor_messages) > 0:
            smessage += " - " + ";".join(motor_messages)
        return (sout, smessage)

    def _move_x(self, x, retry=2):
        for i in range(retry + 1):
            try:
                self.log.debug(
                    "Moving x to position-backlash, %.2f" % (x - self.cart_backslash)
                )
                self._attached_move_x.maw(x - self.cart_backslash)
                self.log.debug("Moving x to requested position, %.2f" % x)
                self._attached_move_x.maw(x)
            except Exception as e:
                if i == retry:
                    self.log.error("Error in x-positioning: %s, giving up" % e)
                else:
                    self.log.warning("Error in x-positioning: %s, retry" % e)
            else:
                return

    def _move_z(self, z, retry=2):
        for i in range(retry + 1):
            try:
                self.log.debug(
                    "Moving z to position-backlash, %.2f" % (z - self.cart_backslash)
                )
                self._attached_move_z.maw(z - self.cart_backslash)
                self.log.debug("Moving z to requested position, %.2f" % z)
                self._attached_move_z.maw(z)
            except Exception as e:
                if i == retry:
                    self.log.error("Error in z-positioning: %s, giving up" % e)
                else:
                    self.log.warning("Error in z-positioning: %s, retry" % e)
            else:
                return

    def _move_xz(self, x, z, retry=2):
        for i in range(retry + 1):
            try:
                self.log.debug(
                    "Moving x,z to position-backlash, %.2f, %.2f"
                    % (x - self.cart_backslash, z - self.cart_backslash)
                )
                self._attached_move_x.move(x - self.cart_backslash)
                self._attached_move_z.maw(z - self.cart_backslash)
                self._attached_move_x.wait()
                self.log.debug("Moving x,z to requested position, %.2f, %.2f" % (x, z))
                self._attached_move_x.move(x)
                self._attached_move_z.maw(z)
                self._attached_move_x.wait()
            except Exception as e:
                if i == retry:
                    self.log.error("Error in xz-positioning: %s, giving up" % e)
                else:
                    self.log.warning("Error in xz-positioning: %s, retry" % e)
            else:
                return

    def _move_angle(self, phi, retry=2):
        for i in range(retry + 1):
            try:
                self._adjust.maw(phi)
            except Exception as e:
                if i == retry:
                    self.log.error("Error in adjuster-positioning: %s, giving up" % e)
                else:
                    self.log.warning("Error in adjuster-positioning: %s, retry" % e)
            else:
                return

    def _engage_retry(self, retry=2):
        for i in range(retry + 1):
            try:
                self._approach.maw(self.engaged)
            except Exception as e:
                if i == retry:
                    self.log.error("Error in approach: %s, giving up" % e)
                else:
                    self.log.warning("Error in approach: %s, retry" % e)
                    self._approach.maw(self.retracted)
                    self._approach.maw(self.engaged)
            else:
                return

    def search_screw(self, step_size=0.2, r_max=5, auto_refine=True, auto_update=False):
        """
        Starting at an approximate position, search for a screw in
        concentric circles with increasing radius.
        Assumes angle of the screw is unknown.
        """
        self._select_driver()

        if self.current_position != (-1, -1):
            angle = self.rotations[self.current_position[0]][self.current_position[1]]
        else:
            angle = 0.0

        self._approach.maw(self.retracted)
        self._adjust.move(angle)

        x_start = self._attached_move_x()
        z_start = self._attached_move_z()

        self.log.info("Searching for screw near %.2f, %.2f" % (x_start, z_start))

        found_screw = False

        for i_r in range(r_max + 1):
            if found_screw:
                break
            r = step_size * i_r
            self.log.info("    search radius = %.2f" % r)
            for i_phi in range(7 * i_r + 1):
                # to keep approximate step size around circle, use 4*i_r angular steps
                phi = 2.0 * np.pi / max(1, 7 * i_r) * i_phi
                xpos = r * np.cos(phi) + x_start
                zpos = r * np.sin(phi) + z_start
                self._move_xz(xpos, zpos)

                self._engage_retry()

                self._move_angle(angle + 60)
                if self._hex_state() == "HexScrewInserted":
                    self._move_angle(angle - self.adjuster_backslash)
                    self._move_angle(angle + self.adjuster_play / 2.0)
                    self._move_angle(angle)
                    found_screw = True
                    break

                self._adjust.move(angle)
                self._approach.maw(self.retracted)

        if found_screw and auto_refine:
            self.log.info(
                "    Screw found at (%.2f, %.2f), trying to refine position"
                % (xpos, zpos)
            )
            self.refine(auto_update=auto_update)
            return True
        else:
            return found_screw

    def refine(self, srange=2.0, sstep=20, auto_update=False):
        """
        If robot could find the screw, use to refine the more exact
        position of the screw center.
        """
        self._select_driver()

        pos_out = []
        vert_out = []

        x_start = self._attached_move_x()
        z_start = self._attached_move_z()

        self.log.info("Refining screw location around %.2f, %.2f" % (x_start, z_start))

        self._approach.maw(self.retracted)

        for i in range(sstep):
            self._move_x(x_start + srange * (i - sstep / 2) / (sstep - 1))
            self._engage_retry()
            pos_out.append(
                [self._attached_move_x(), self._hex_state() == "HexScrewInserted"]
            )
            self._approach.maw(self.retracted)

        pos_out = np.array(pos_out)
        x_insertions = pos_out[pos_out[:, 1] == 1, 0]
        self.log.info("  Insertions in x-scan: %s" % (x_insertions))
        if len(x_insertions) == 0:
            raise ValueError("Scan never inserted into screw")
        self._move_x(x_insertions.mean())

        for j in range(sstep):
            self._move_z(z_start + srange * (j - sstep / 2) / (sstep - 1))
            self._approach.maw(self.engaged)
            vert_out.append(
                [self._attached_move_z(), self._hex_state() == "HexScrewInserted"]
            )
            self._approach.maw(self.retracted)

        vert_out = np.array(vert_out)
        self.log.info("  Insertions in z-scan: %s" % (vert_out[vert_out[:, 1] == 1, 0]))

        # calculate new center
        cen_pos = pos_out[pos_out[:, 1] == 1, 0].mean()
        cen_vert = vert_out[vert_out[:, 1] == 1, 0].mean()

        self._move_xz(cen_pos, cen_vert)

        if auto_update:
            self.update_position()

        return pos_out, vert_out

    def update_position(self):
        # Change the stored location for the current screw
        self.doRead()
        if self.current_position != (-1, -1):
            # dict parameter is immutable, create a copy and modify that
            pos = dict([(k, dict(v)) for k, v in self.positions.items()])
            pos[self.current_position[0]][self.current_position[1]] = (
                self._attached_move_x(),
                self._attached_move_z(),
            )
            self.positions = pos
            self.log.info(
                "Updated stored position for screw (%i, %02i) to (%.2f, %.2f)"
                % (
                    self.current_position[0],
                    self.current_position[1],
                    self.positions[self.current_position[0]][self.current_position[1]][
                        0
                    ],
                    self.positions[self.current_position[0]][self.current_position[1]][
                        1
                    ],
                )
            )

    def adjust(self, angle):
        self.doRead()
        if self.current_position == (-1, -1):
            return
        if self._hex_state() in ["HexScrewInTransition", "HexScrewFullyOut"]:
            self._engage()
        if self._hex_state() != "HexScrewInserted":
            # issue with insertion
            self.log.warning("Screw driver not inserted correctly, aborting")
            return False
        self.log.debug(
            "Adjusting to position-play/2-backlash, %.2f"
            % (angle - self.adjuster_play / 2.0 - self.adjuster_backslash)
        )
        self._move_angle(angle - self.adjuster_play / 2.0 - self.adjuster_backslash)
        # always overshoot with the expected play
        self.log.debug(
            "Adjusting to position+play/2, %.2f" % (angle + self.adjuster_play / 2.0)
        )
        self._move_angle(angle + self.adjuster_play / 2.0)
        # move back to desired angle for extractoin
        self.log.debug("Releasing screw, %.2f" % (angle))
        self._move_angle(angle)
        self.log.debug(
            "Storing rotation for position (%i, %02i)" % self.current_position
        )

        rotations = dict([(k, dict(v)) for k, v in self.rotations.items()])

        rotations[self.current_position[0]][self.current_position[1]] = angle
        self.rotations = rotations

    def adjust_position(self, delta):
        """
        Make a relative movement with the current adjuster to translate
        the corresponding mirror by ghe given offset delta [mm].
        """
        self.doRead()
        if self.current_position == (-1, -1):
            return
        screw, group = self.current_position
        if screw in self.vertical_screws:
            self.log.debug(f"Moving vertical mirror by {delta:.3f}")
            newpos = self._adjust() + delta * self.vertical_ratio
        else:
            self.log.debug(f"Moving vertical mirror by {delta:.3f}")
            newpos = self._adjust() + delta * self.horizontal_ratio
        self.adjust(newpos)

    def save_data(self, fname=None):
        if fname is None:
            fname = self.position_data
        data = {
            "positions": dict([(k, dict(v)) for k, v in self.positions.items()]),
            "rotations": dict([(k, dict(v)) for k, v in self.rotations.items()]),
        }
        yaml.dump(data, open(fname, "w"), indent=2, sort_keys=True)

    def load_data(self, fname=None):
        if fname is None:
            fname = self.position_data
        data = yaml.load(open(fname, "r"), yaml.FullLoader)
        self.positions = data["positions"]
        self.rotations = data["rotations"]
        self.calculate_zeros()

    def confirm_all(self):
        self.log.info("Confirming screws...")
        for group in range(1, 16):
            for item in self.positions.keys():
                if self._confirmed[item][group]:
                    continue
                self.log.info("  position (%i, %02i)" % (item, group))
                self.doStart((item, group))
                self._attached_move_x.wait()
                self._attached_move_z.wait()
                self._attached_adjust1.wait()
                self._attached_adjust2.wait()
                self._engage()
                if self._hex_state() == "HexScrewInserted":
                    self.log.info("        confirmed")
                    self._confirmed[item][group] = True
                else:
                    self.log.info("        " + self._hex_state())

    def reference_screw(self, nrot0=15):
        """
        Use the lower hard stop of the adjuster to reference the screw
        absolute rotation position.
        Will drive adjuster negative until the motor stops following
        then it moves nrot0 rotations forward and defines this as new zero.
        """
        self.doRead()
        if self.current_position == (-1, -1):
            return
        if self._hex_state() in ["HexScrewInTransition", "HexScrewFullyOut"]:
            self._engage()
        if self._hex_state() != "HexScrewInserted":
            # issue with insertion
            self.log.warning("Screw driver not inserted correctly, aborting")
            return False
        self.log.info("Moving screw to lower limit")
        try:
            self._adjust.maw(-15000)
        except Exception:
            pass
        lpos = self._adjust()
        self.log.info("   screw stopped moving at %.1f°" % lpos)
        lpos_partial = (lpos + 180) % 360 - 180  # partial rotation of this position
        dest = self.rotations[self.current_position[0]][self.current_position[1]]
        if dest < (-nrot0 * 360):
            # make sure the destination is not smaller then the lower limit
            dest = -(nrot0 - 1) * 360
            rotations = dict([(k, dict(v)) for k, v in self.rotations.items()])
            rotations[self.current_position[0]][self.current_position[1]] = dest
            self.rotations = rotations
        temp_dest = lpos - lpos_partial + nrot0 * 360 + dest
        self.log.debug("    moving to calculated position %.1f" % temp_dest)
        for i in range(15):
            self._adjust.reset()
            try:
                self._adjust.maw(
                    temp_dest - self.adjuster_play / 2.0 - self.adjuster_backslash
                )
            except Exception:
                continue
            else:
                break
        self._move_angle(temp_dest + self.adjuster_play / 2.0)
        self._move_angle(temp_dest)
        self.log.debug("    move driver back to nominal position %.1f" % dest)
        self._disengage()
        self._move_angle(dest)
        return True


class SeleneMetrology(SeleneCalculator, BaseSequencer):
    parameters = {
        "cart_center": Param(
            "Cart position of ellipse center",
            mandatory=False,
            userparam=True,
            default=3500.0,
            unit="mm",
        ),
        "eta_v": Param(
            "Nominal reflection angle from interferometer head to retroreflector",
            mandatory=False,
            userparam=True,
            default=14.81,
            unit="deg",
        ),
        "delta_v": Param(
            "Nominal distance between XZ plane and retroreflector",
            mandatory=False,
            userparam=True,
            default=120.0,
            unit="mm",
        ),
        "eta_h1": Param(
            "Nominal reflection angle from interferometer head to retroreflector",
            mandatory=False,
            userparam=True,
            default=16.39,
            unit="deg",
        ),
        "delta_h1": Param(
            "Nominal distance between XZ plane and retroreflector",
            mandatory=False,
            userparam=True,
            default=70.0,
            unit="mm",
        ),
        "zret_h1": Param(
            "Nominal distance between XY plane and retroreflector",
            mandatory=False,
            userparam=True,
            default=50.0,
            unit="mm",
        ),
        "zcol_h1": Param(
            "Nominal distance between XY plane and collimator",
            mandatory=False,
            userparam=True,
            default=120.0,
            unit="mm",
        ),
        "eta_h2": Param(
            "Nominal reflection angle from interferometer head to retroreflector",
            mandatory=False,
            userparam=True,
            default=15.47,
            unit="deg",
        ),
        "delta_h2": Param(
            "Nominal distance between XZ plane and retroreflector",
            mandatory=False,
            userparam=True,
            default=80.0,
            unit="mm",
        ),
        "zret_h2": Param(
            "Nominal distance between XY plane and retroreflector",
            mandatory=False,
            userparam=True,
            default=10.0,
            unit="mm",
        ),
        "zcol_h2": Param(
            "Nominal distance between XY plane and collimator",
            mandatory=False,
            userparam=True,
            default=160.0,
            unit="mm",
        ),
        "delta_x": Param(
            "Nominal x-distance of retroreflector and cart center",
            mandatory=False,
            userparam=True,
            default=-15.0,
            unit="mm",
        ),
        "if_offset_u_h1": Param(
            "Deviation of laser path length as determined at center",
            settable=True,
            internal=True,
            default=0.0,
            unit="mm",
        ),
        "if_offset_u_h2": Param(
            "Deviation of laser path length as determined at center",
            settable=True,
            internal=True,
            default=0.0,
            unit="mm",
        ),
        "if_offset_u_v1": Param(
            "Deviation of laser path length as determined at center",
            settable=True,
            internal=True,
            default=0.0,
            unit="mm",
        ),
        "if_offset_u_v2": Param(
            "Deviation of laser path length as determined at center",
            settable=True,
            internal=True,
            default=0.0,
            unit="mm",
        ),
        "if_offset_d_h1": Param(
            "Deviation of laser path length as determined at center",
            settable=True,
            internal=True,
            default=0.0,
            unit="mm",
        ),
        "if_offset_d_h2": Param(
            "Deviation of laser path length as determined at center",
            settable=True,
            internal=True,
            default=0.0,
            unit="mm",
        ),
        "if_offset_d_v1": Param(
            "Deviation of laser path length as determined at center",
            settable=True,
            internal=True,
            default=0.0,
            unit="mm",
        ),
        "if_offset_d_v2": Param(
            "Deviation of laser path length as determined at center",
            settable=True,
            internal=True,
            default=0.0,
            unit="mm",
        ),
        "last_raw": Param(
            "Measured raw distances",
            type=tupleof(float, float, float, float),
            default=(np.nan, np.nan, np.nan, np.nan),
            settable=True,
            internal=True,
            unit="mm",
        ),
        "last_delta": Param(
            "Calculated deviaition for 4 screws at current location from last measurement",
            type=tupleof(float, float, float, float),
            default=(np.nan, np.nan, np.nan, np.nan),
            settable=True,
            internal=True,
            unit="mm",
        ),
    }

    attached_devices = {
        "m_cart": Attach("Metrology cart", LockedDevice),
        "interferometer": Attach("Attached interferometer", MultilineController),
        "ch_u_h1": Attach(
            "Interferometer channel for horizontal mirror up-stream", MultilineChannel
        ),
        "ch_u_h2": Attach(
            "Interferometer channel for horizontal mirror up-stream", MultilineChannel
        ),
        "ch_u_v1": Attach(
            "Interferometer channel for vertical mirror up-stream", MultilineChannel
        ),
        "ch_u_v2": Attach(
            "Interferometer channel for vertical mirror up-stream", MultilineChannel
        ),
        "ch_d_h1": Attach(
            "Interferometer channel for horizontal mirror down-stream", MultilineChannel
        ),
        "ch_d_h2": Attach(
            "Interferometer channel for horizontal mirror down-stream", MultilineChannel
        ),
        "ch_d_v1": Attach(
            "Interferometer channel for vertical mirror down-stream", MultilineChannel
        ),
        "ch_d_v2": Attach(
            "Interferometer channel for vertical mirror down-stream", MultilineChannel
        ),
    }

    def _getWaiters(self):
        return [self._attached_m_cart, self._attached_interferometer]

    def doInit(self, dummy=None):
        self._sa = np.sqrt(self._sc**2 + self._sb**2)
        self._cache.addCallback(
            self._attached_m_cart, "value", self._on_status_change_external
        )
        self._cache.addCallback(
            self._attached_m_cart, "status", self._on_status_change_external
        )
        self._cache.addCallback(
            self._attached_interferometer, "status", self._on_status_change_external
        )

    def shutdown(self):
        self._cache.removeCallback(
            self._attached_m_cart, "value", self._on_status_change_external
        )
        self._cache.removeCallback(
            self._attached_m_cart, "status", self._on_status_change_external
        )
        self._cache.removeCallback(
            self._attached_interferometer, "status", self._on_status_change_external
        )
        BaseSequencer.shutdown(self)

    def _on_status_change_external(self, key, value, time):
        self._cache.invalidate(self, "status")

    def doRead(self, maxage=0):
        """
        Position is the location on mirror and mirror number counting from up-stream.
        Location on mirror is -1: up-stream screw, 0: center, 1: down-stream screw.
        """
        pos = self._attached_m_cart() - self.cart_center
        if abs(pos) > 50:
            pos = self._x_for_cart(pos)
        mirror = int(
            (pos + self._mw / 2) // self._mw + 8
        )  # mirrors are 480 wide and 8 is the central one
        rpos = (
            pos + self._mw / 2
        ) % self._mw - self._mw / 2  # relative position on mirror
        if abs(rpos) < 10:
            return (0, mirror)
        elif (abs(rpos) + self._sx - self._mw / 2) < 10:
            if rpos < 0:
                return (-1, mirror)
            else:
                return (1, mirror)
        else:
            return (rpos, mirror)

    def valueInfo(self):
        return (Value("Relative Position", unit=""), Value("Mirror", unit=""))

    def _generateSequence(self, position):
        # TODO: Special case for 1/15 outer positions not nominally reachable
        if (
            len(position) == 2
            and position[0] in [-1, 0, 1]
            and position[1] in range(1, 16)
        ):
            rel_pos, mirror = position
        else:
            raise ValueError(
                "Position should be tuple (rel. location, mirror) w/ rel. location in [-1,0,1]"
            )
        calc_pos = self._mw * (mirror - 8) + rel_pos * (self._mw / 2 - self._sx)
        dest_pos = self.cart_center + self._cart_for_x(calc_pos)

        # reset last values before starting to move, so any value but nan should be for the current location
        self.last_raw = (np.nan, np.nan, np.nan, np.nan)
        self.last_delta = (np.nan, np.nan, np.nan, np.nan)

        if abs(calc_pos) < 300:
            measure_channels = [
                self._attached_ch_d_v1.channel,
                self._attached_ch_d_v2.channel,
                self._attached_ch_d_h1.channel,
                self._attached_ch_d_h2.channel,
                self._attached_ch_u_v1.channel,
                self._attached_ch_u_v2.channel,
                self._attached_ch_u_h1.channel,
                self._attached_ch_u_h2.channel,
            ]
        elif calc_pos > 0:
            measure_channels = [
                self._attached_ch_d_v1.channel,
                self._attached_ch_d_v2.channel,
                self._attached_ch_d_h1.channel,
                self._attached_ch_d_h2.channel,
            ]
        else:
            measure_channels = [
                self._attached_ch_u_v1.channel,
                self._attached_ch_u_v2.channel,
                self._attached_ch_u_h1.channel,
                self._attached_ch_u_h2.channel,
            ]

        return [
            SeqDev(self._attached_m_cart, dest_pos),  # move to location
            SeqMethod(
                self._attached_interferometer, "measure", measure_channels
            ),  # make a measurement
            SeqWait(self._attached_interferometer),  # make a measurement
            SeqMethod(self, "_calc_current_difference"),  # analyse and store result
        ]

    def measure(self):
        """
        Generate a sequence that is just measuring without moving and run it.
        """
        if self._seq_is_running():
            if self._mode == SIMULATION:
                self._seq_thread.join()
                self._seq_thread = None
            else:
                raise MoveError(
                    self,
                    "Cannot start device, sequence is still "
                    "running (at %s)!" % self._seq_status[1],
                )
        # reset last values before starting to move, so any value but nan should be for the current location
        self.last_raw = (np.nan, np.nan, np.nan, np.nan)
        self.last_delta = (np.nan, np.nan, np.nan, np.nan)

        cpos = self._attached_m_cart()
        xpos = self._x_for_cart(cpos - self.cart_center)
        if abs(xpos) < 300:
            measure_channels = [
                self._attached_ch_d_v1.channel,
                self._attached_ch_d_v2.channel,
                self._attached_ch_d_h1.channel,
                self._attached_ch_d_h2.channel,
                self._attached_ch_u_v1.channel,
                self._attached_ch_u_v2.channel,
                self._attached_ch_u_h1.channel,
                self._attached_ch_u_h2.channel,
            ]
        elif xpos > 0:
            measure_channels = [
                self._attached_ch_d_v1.channel,
                self._attached_ch_d_v2.channel,
                self._attached_ch_d_h1.channel,
                self._attached_ch_d_h2.channel,
            ]
        else:
            measure_channels = [
                self._attached_ch_u_v1.channel,
                self._attached_ch_u_v2.channel,
                self._attached_ch_u_h1.channel,
                self._attached_ch_u_h2.channel,
            ]
        sequence = [
            SeqMethod(
                self._attached_interferometer, "measure", measure_channels
            ),  # make a measurement
            SeqWait(self._attached_interferometer),  # make a measurement
            SeqMethod(self, "_calc_current_difference"),  # analyse and store result
        ]
        self._startSequence(sequence)

    def _calc_current_difference(self):
        # run after a measurement is complete to get the screw deviations
        self.log.debug("Measurement done, store raw lengths and deviations")
        cpos = self._attached_m_cart()
        xpos = self._x_for_cart(cpos - self.cart_center)

        # nominal lengths at current location
        nv, nh1, nh2 = self._nominal_path_lengths(cpos - self.cart_center)

        if xpos > 0:
            self.last_raw = (
                self._attached_ch_d_v1.read(maxage=0),
                self._attached_ch_d_v2.read(maxage=0),
                self._attached_ch_d_h1.read(maxage=0),
                self._attached_ch_d_h2.read(maxage=0),
            )
            self.log.debug(
                "Using downstream collimators; raw lengths: %s" % str(self.last_raw)
            )
            lv1 = nv - self.if_offset_d_v1
            lv2 = nv - self.if_offset_d_v2
            lh1 = nh1 - self.if_offset_d_h1
            lh2 = nh2 - self.if_offset_d_h2
        else:
            self.last_raw = (
                self._attached_ch_u_v1.read(maxage=0),
                self._attached_ch_u_v2.read(maxage=0),
                self._attached_ch_u_h1.read(maxage=0),
                self._attached_ch_u_h2.read(maxage=0),
            )
            self.log.debug(
                "Using upstream collimators; raw lengths: %s" % str(self.last_raw)
            )
            lv1 = nv - self.if_offset_u_v1
            lv2 = nv - self.if_offset_u_v2
            lh1 = nh1 - self.if_offset_u_h1
            lh2 = nh2 - self.if_offset_u_h2
        dlv1 = self.last_raw[0] - lv1
        dlv2 = self.last_raw[1] - lv2
        dlh1 = self.last_raw[2] - lh1
        dlh2 = self.last_raw[3] - lh2

        self.last_delta = self._path_delta_to_screw_delta(dlv1, dlv2, dlh1, dlh2)
        self.log.debug(
            "  From length differences %s calculate deviations %s"
            % ((dlv1, dlv2, dlh1, dlh2), self.last_delta)
        )

    def calibrate(self):
        """
        Use measurement at center position to calibrate the
        interferometer channel lengths measured.
        """
        self.log.info("Performing calibration of interferometer lengths")
        self._attached_m_cart.maw(self.cart_center)
        self._attached_interferometer.measure()
        self._attached_interferometer.wait()

        v, h1, h2 = self._nominal_path_lengths(0.0)
        for li, chi in [
            (v, "u_v1"),
            (v, "u_v2"),
            (v, "d_v1"),
            (v, "d_v2"),
            (h1, "u_h1"),
            (h2, "u_h2"),
            (h1, "d_h1"),
            (h2, "d_h2"),
        ]:
            ch = getattr(self, f"_attached_ch_{chi}")
            if ch.status()[0] == status.OK:
                setattr(self, f"if_offset_{chi}", li - ch())
            else:
                self.log.warning(
                    "Channel %s not measured correctly (%s)" % (chi, ch._name)
                )


#
# class SeleneGuide(BaseSequencer):
#     parameters = {
#         'major_axis': Param('Major semi-axis of the ellipse', type=float,
#                             unit='mm',
#                             settable=False, mandatory=True,
#                             userparam=False,
#                             category='general'),
#         'minor_axis': Param('Minor semi-axis of the ellipse', type=float,
#                             unit='mm',
#                             settable=False, mandatory=True,
#                             userparam=False,
#                             category='general'),
#         'segment_length': Param('Length of one mirror segment', type=float,
#                                 unit='mm',
#                                 settable=False, mandatory=True,
#                                 userparam=False,
#                                 category='general'),
#         'screws_semidistance': Param('Semidistance between screws along '
#                                      'x-axis', mandatory=True,
#                                      userparam=False, unit='mm', ),
#         'adjuster_rows': Param('Position of the screws along X-axis',
#                                type=list, settable=True,
#                                mandatory=True,
#                                userparam=False, unit='mm', ),
#         'adjuster_columns': Param('Position of the screws along Z-axis',
#                                   type=list, settable=True,
#                                   mandatory=True,
#                                   userparam=False, unit='mm', ),
#         'segments': Param('Number of segments that compose the guide',
#                           type=int, mandatory=True, userparam=False, ),
#         'vertical_ratio': Param('', mandatory=True,
#                                 userparam=False, unit='mm/deg', ),
#         'horizontal_ratio': Param('', mandatory=True,
#                                   userparam=False, unit='mm/deg', ),
#         'adjuster_angles': Param('Current rotation angles', type=list,
#                                  mandatory=True,
#                                  userparam=True, settable=True, unit='deg', ),
#         'adjuster_positions': Param('Screws position', type=list,
#                                     mandatory=True, settable=True,
#                                     userparam=False, unit='mm', ),
#         # 'driver_dx': Param('', mandatory=True,
#         #                    userparam=False, unit='mm', ),
#     }
#
#     parameter_overrides = {
#         'precision': Override(userparam=False, default=0.01),
#         'lowlevel': Override(default=False),
#     }
#
#     attached_devices = {
#         'rx': Attach('Adjustment X-axis motor', EpicsMotor),
#         'rz': Attach('Adjustment Z-axis motor', EpicsMotor),
#         'screwdriver': Attach('Adjustment screwdriver', Screwdriver),
#         #  'interferometer': Attach('Interferometer', MirrorDistance),
#         #  'm_cart': Attach('Metrology cart', LockedDevice),
#         'measurement': Attach('Guide measurement system',
#                               SeleneMeasurementHandler)
#     }
#
#     _offset_values = []
#     _actions = []
#
#     def _generateSequence(self, _):  # pylint: disable=W0221
#         print('_generateSequence')
#         return self._actions
#
#     def doInit(self, dummy=None):
#         segment_len = self.segment_length
#         distance = self.screws_semidistance
#         # self._adjuster_columns = [
#         #     [-distance + (i - 7) * segment_len,
#         #      distance + (i - 7) * segment_len]
#         #     for i in range(self.segments)]
#
#         # FIX
#         # self.adjuster_columns = [[60.0, 455.1, 100],
#         # 				    [455.1, 100, 100] ]
#         # self.adjuster_rows = [[157.0, 123.5, 187.5],
#         #                                  [212.7, 187.5, 222.5]]
#
#         if not self.adjuster_angles:
#             self.log.warning('Initialize empty \'adjuster_angles\'')
#             self.adjuster_angles = [[[0] * 3] * 2] * \
#                                               self.segments
#         if not self.adjuster_positions:
#             self.log.warning('Initialize empty \'adjuster_positions\'')
#             self.adjuster_positions = [[[0] * 3] * 2] * self.segments
#
#     def _compute_adjustement_sequence(self):
#         self._adjust_guide()
#
#     def doStart(self, target=None):
#         #        self.adjust_guide()
#         BaseSequencer.doStart(self, target)
#
#     def doRead(self, maxage=0):
#         return self._find_screw_indices()
#
#     # def doStatus(self, maxage=0):
#     #     return None
#
#     # def doStatus(self, maxage=0):
#     #     return None
#
#     # def _position_for(self, segment, step):
#     #     x_m = self.adjuster_columns[segment][step]
#     #     self._actions.append(SeqDev(self._attached_rx, x_m))
#
#     # def _measure_current_position(self, segment, step):
#     #     x_m = self.adjuster_columns[segment][step]
#     #     self._actions.append(
#     #         SeqCall(self._attached_measurement.measure, x_m))
#
#     def _get_offsets(self, step, index):
#         offset_values = self._attached_measurement.doRead()
#         self.log.warning(offset_values)
#         delta_pos = 10
#         if (step == 0 and index == 2) or (step == 1 and index > 0):
#             # delta_pos = interpolate()
#             delta_rot = delta_pos / self.horizontal_ratio
#         else:
#             # delta_pos = interpolate()
#             delta_rot = delta_pos / self.vertical_ratio
#         return delta_pos, delta_rot
#
#     def _adjust(self, rot_from, rot_to):
#         # if self._attached_rx.read() > 0:
#         #     drive = self._attached_r1t
#         # else:
#         #     drive = self._attached_r2t
#         drive = self._attached_screwdriver
#
#         drive.doStart([rot_from, rot_to, ])
#         self._attached_screwdriver.wait()
#
#     def _mock_adjust_guide_segment(self, segment, step, index):
#         self._mock_position_for(segment, step)
#         _offset_values = self._attached_measurement.read()
#
#     def _adjust_guide(self):
#         for segment in range(self.segments):
#             for step in range(2):
#                 # append to SeqCall list
#                 # self._position_for(segment, step)
#                 self._actions.append(SeqCall(self.move_to_position, segment,
#                                              step))
#
#                 # FIXME: Doesn't this require the index too?
#                 self._measure_current_position(self, segment, step)
#                 # This must be sequential too!
#                 _offset_values = self._attached_measurement.read()
#                 for index in range(3):
#                     self._actions.append(
#                         SeqCall(self.move_to_position, segment,
#                                 step, index))
#
#                     rot_from = self._adjuster_angles[segment][
#                         step][index]
#                     # pos_from = self._adjuster_positions[segment][
#                     #     step][index]
#                     delta_rot, delta_pos = self._get_offsets(step, index)
#                     self.log.info('({},{},{}) -> delta_rot: {'
#                                   '}\tdelta_pos: {}'.format(segment,
#                                                             step,
#                                                             index,
#                                                             delta_rot,
#                                                             delta_pos))
#                     # self._adjust(rot_from, rot_from + delta_rot)
#                     # FIXME: check success
#                     success = True
#                     if success:
#                         self.adjuster_angles[segment][step][
#                             index] += \
#                             delta_rot
#                         self.adjuster_positions[segment][step][
#                             index] += \
#                             delta_pos
#
#     # Determine the screw indices correspondig to the current position. If
#     # the current position in more than 'tolerance' cm far from any screw,
#     # returns None (i.e. assumes that we are not at any screw)
#     def _find_x_index(self, tolerance=.5):
#         x_pos = self._attached_rx()
#         for segment, segment_values in enumerate(self.adjuster_columns):
#             if abs(segment_values[0] - x_pos) < tolerance:
#                 return segment, 0
#             if abs(segment_values[1] - x_pos) < tolerance:
#                 return segment, 1
#         return None, None
#
#     def _find_z_index(self, tolerance=.5):
#         z_pos = self._attached_rz()
#         for step, step_values in enumerate(self.adjuster_rows):
#             if abs(step_values[0] - z_pos) < tolerance:
#                 return step, 0
#             if abs(step_values[1] - z_pos) < tolerance:
#                 return step, 1
#         return None, None
#
#     def _find_screw_indices(self, tolerance=.5):
#         segment, x_index = self._find_x_index(tolerance)
#         step, z_index = self._find_z_index(tolerance)
#         # TODO: needs review
#         if z_index is None or x_index is None: #or x_index != z_index:
#             self.log.info('Screwdriver not in a screw position')
#             return None, None, None
#         return segment, step, 0
#
#     def _update_adjuster_angle(self):
#         segment, column, row = self._find_screw_indices()
#         if None in [segment, column, row]:
#             self.log.info('Not in a screw position, no angle to update')
#             return
#         current = self.adjuster_angles
#         angle = self._attached_screwdriver._attached_angle()
#         updated = [[list(curcol) for curcol in curseg] for curseg in current]
#         updated[segment][column][row]=angle
#         self._setROParam('adjuster_angles', updated)
#
#     def update_screw_position(self):
#         segment, column, row = self._find_screw_indices(tolerance=5.0)
#         if None in [segment, column, row]:
#             self.log.info('Not in a screw position, no positon to update')
#             return
#         cx = self._attached_rx.read()
#         cz = self._attached_rz.read()
#         cols = [list(curseg) for curseg in self.adjuster_columns]
#         rows = [list(curstep) for curstep in self.adjuster_rows]
#         self.log.info('Updating column,row from %.2f,%.2f to %.2f,%.2f'%
#                       (cols[segment][row], rows[column][row], cx, cz))
#         cols[segment][row]=cx
#         rows[column][row]=cz
#         self._setROParam('adjuster_columns', cols)
#         self._setROParam('adjuster_rows', rows)
#
#     def disengage(self):
#         if self._attached_screwdriver._is_engaged():
#             self._update_adjuster_angle()
#             self._attached_screwdriver._disengage()
#
#     def engage(self):
#         segment, step, index = self._find_screw_indices()
#         if not segment in [segment, step, index]:
#             angle = self.adjuster_angles[segment][step][index]
#             if self._attached_screwdriver._attached_angle() != angle:
#                 self.log.info('Current screwdriver rotation doesn\'t match '
#                               'screw angle, correcting rotation')
#                 self._attached_screwdriver.rotate_to(angle)
#         self._attached_screwdriver._engage()
#
#     def move_to_position(self, segment, step, index=0):
#         if self._attached_screwdriver._is_engaged():
#             self.disengage()
#         self._attached_rx.move(self.adjuster_columns[segment][step])
#         self._attached_rz.move(self.adjuster_rows[step][index])
#         self._attached_screwdriver._attached_angle.move(
#             self.adjuster_angles[segment][step][index])
#         self._attached_rx.wait()
#         self._attached_rz.wait()
#         self._attached_screwdriver._attached_angle.wait()
#
#     # TESTING
#     # FIXME: Doesn't this require the index (i.e. z position) too?
#     def measure_position(self, segment, step, index=None):
#         x_m = self.adjuster_columns[segment][step]
#         self._attached_measurement._position_to_measure(x_m)
#         self._attached_measurement.measure(x_m)
#         self._attached_measurement.wait()
