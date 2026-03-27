from enum import StrEnum

from nicos.core import (
    SIMULATION,
    Attach,
    ConfigurationError,
    HasPrecision,
    LimitError,
    MoveError,
    Override,
    oneof,
)
from nicos.devices.abstract import MappedMoveable
from nicos.devices.generic.sequence import SeqDev, SequencerMixin
from nicos.utils import num_sort
from nicos_ess.devices.mapped_controller import MappedController


class ArmPositions(StrEnum):
    InBeam = "In beam"
    Parked = "Parked"
    Intermediate = "Intermediate"


class XPositions(StrEnum):
    Parked = "Parked"
    Pos1 = "Xpos BS1"
    Pos2 = "Xpos BS2"
    Pos3 = "Xpos BS3"
    Pos4 = "Xpos BS4"
    Pos5 = "Xpos BS5"


class LokiBeamstopArmPositioner(MappedController):
    def doInit(self, mode):
        super().doInit(mode)

    def _check_mapped_keys(self, mapping):
        expected = {p.value for p in ArmPositions}
        if set(mapping.keys()) != expected:
            raise ConfigurationError(
                f"Only {list(expected)} are allowed as mapped positions"
            )

    def _check_mapped_values(self, mapping):
        for position in mapping.values():
            self._check_limits(position)

    def _check_limits(self, position):
        device = self._attached_controlled_device
        limits = device.userlimits
        is_allowed, reason = device.isAllowed(position)
        if not is_allowed:
            raise LimitError(
                f"Mapped position {position} for {device._name} is outside user limits {limits}"
            )

    def doWriteMapping(self, mapping):
        self._check_mapped_keys(mapping)
        self._check_mapped_values(mapping)
        self.valuetype = oneof(*sorted(mapping, key=num_sort))

    def _mapReadValue(self, value):
        if isinstance(self._attached_controlled_device, HasPrecision):
            for k, v in self.mapping.items():
                if abs(v - value) < self._attached_controlled_device.precision:
                    return k
        inverse_mapping = {v: k for k, v in self.mapping.items()}
        mapped_value = inverse_mapping.get(value, None)
        if mapped_value:
            return mapped_value
        if (
            ArmPositions.Parked in self.mapping.keys()
            and value > self.mapping[ArmPositions.Parked]
        ):
            return "Above park position"
        if (
            ArmPositions.InBeam in self.mapping.keys()
            and value < self.mapping[ArmPositions.InBeam]
        ):
            return "Below in-beam position"
        return "In between"


class LokiBeamstopController(SequencerMixin, MappedMoveable):
    attached_devices = {
        "bsx_positioner": Attach("Positioner for beamstop x", MappedController),
        "bsy_positioner": Attach("Positioner for beamstop y", MappedController),
        "bs1_positioner": Attach("Positioner for beamstop z1", MappedController),
        "bs2_positioner": Attach("Positioner for beamstop z2", MappedController),
        "bs3_positioner": Attach("Positioner for beamstop z3", MappedController),
        "bs4_positioner": Attach("Positioner for beamstop z4", MappedController),
        "bs5_positioner": Attach("Positioner for beamstop z5", MappedController),
    }

    parameter_overrides = {
        "mapping": Override(
            mandatory=False, settable=False, userparam=False, volatile=True
        ),
    }

    def doPreinit(self, mode):
        self._all_attached = {
            "x": self._attached_bsx_positioner,
            "y": self._attached_bsy_positioner,
            "monitor": self._attached_bs1_positioner,
            "beamstop 2": self._attached_bs2_positioner,
            "beamstop 3": self._attached_bs3_positioner,
            "beamstop 4": self._attached_bs4_positioner,
            "beamstop 5": self._attached_bs5_positioner,
        }
        self._full_mapping = self._get_mapped_positions()

    def doInit(self, mode):
        self._setROParam("mapping", self._get_mapped_positions())
        super().doInit(mode)
        self.valuetype = oneof(*self._get_mapped_positions().keys())

    def doRead(self, maxage=0):
        return self._mapReadValue(self._readRaw(maxage))

    def _readRaw(self, maxage=0):
        return tuple(channel.read(maxage) for channel in self._all_attached.values())

    def _mapReadValue(self, value):
        inverse_mapping = {v: k for k, v in self._full_mapping.items()}
        mapped_value = inverse_mapping.get(value, None)
        if not mapped_value:
            return "In between"
        return mapped_value

    def doReadMapping(self):
        return self._get_mapped_positions()

    def _checkFailed(self, step, action, exc_info):
        if isinstance(exc_info[0], LimitError):
            pass
        else:
            return exc_info[1]

    def doStart(self, target):
        if target == self.read():
            return

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

        sequence = self._generateSequence(target)
        print("target sequence:", sequence)
        self._startSequence(sequence)

    def _generateSequence(self, target: str):
        """
        Sequence when parking:
            The sequence first moves the beamstop arms away from the detector,
            then raises the arms to their parked positions.
        Sequence when moving arms to in beam position:
            The sequence first moves the beamstop arms down into the beam,
            then moves the arms into the center of the beam and
            finally moves the arms towards the detector.

        Returns:
            List of SeqDevs or tuples of multiple parallel SeqDevs
        """
        normalized_target = self.normalize(target)
        normalized_value = self.normalize(self.read())

        if "park" in normalized_target:
            return self._all_devices_to_park()

        request = self._extract_arms(normalized_target)
        current = self._extract_arms(normalized_value)

        if request["beamstop"] and request["beamstop"] == current["beamstop"]:
            if request["monitor"]:
                return [self._device_to_in_beam("monitor")]
            else:
                return [self._device_to_park("monitor")]

        seq = []
        seq.extend(self._all_devices_to_park())

        if request["monitor"] and request["beamstop"]:
            # beamstop needs to lower slightly first for twincat to update limits
            seq.append(self._device_to_intermediate(request["beamstop"]))
            seq.append(
                self._devices_to_in_beam([request["beamstop"], request["monitor"]])
            )

        elif request["beamstop"]:
            seq.append(self._device_to_in_beam(request["beamstop"]))
        elif request["monitor"]:
            seq.append(self._device_to_in_beam("monitor"))

        seq.append(self._device_to_in_beam("y"))
        seq.append(self._x_device_to_x_pos(target))

        return seq

    def _extract_arms(self, string):
        arms = [arm.strip() for arm in string.split("+")]
        beamstop = next((arm for arm in arms if arm.startswith("beamstop")), False)
        monitor = "monitor" if "monitor" in arms else False
        return {
            "beamstop": beamstop,
            "monitor": monitor,
        }

    def _device_to_park(self, device_name):
        device = self._all_attached[device_name]
        return SeqDev(device, ArmPositions.Parked)

    def _device_to_in_beam(self, device_name):
        device = self._all_attached[device_name]
        return SeqDev(device, ArmPositions.InBeam)

    def _device_to_intermediate(self, device_name):
        device = self._all_attached[device_name]
        return SeqDev(device, ArmPositions.Intermediate)

    def _devices_to_in_beam(self, device_names):
        return tuple(self._device_to_in_beam(name) for name in device_names)

    def _devices_to_park(self, device_names):
        return tuple(self._device_to_park(name) for name in device_names)

    def _x_device_to_x_pos(self, target):
        x_pos = self._get_x_pos(target)
        device = self._all_attached["x"]
        return SeqDev(device, x_pos)

    def _all_devices_to_park(self):
        device_names_not_parked = self._get_non_parked_device_names()
        seq = []
        if "x" in device_names_not_parked:
            seq.append(self._device_to_park("x"))
        arms = [
            key
            for key in device_names_not_parked
            if "beamstop" in key or "monitor" in key
        ]
        if len(arms) > 0:
            seq.append(self._devices_to_park(arms))
        return seq

    def _get_non_parked_device_names(self):
        all_device_names = set(self._all_attached.keys())
        device_names_in_park = set(
            self._get_keys_matching_read_value(ArmPositions.Parked)
        )
        return list(all_device_names - device_names_in_park)

    def normalize(self, string):
        return string.strip().lower()

    def _get_x_pos(self, target):
        mapping = self._get_mapped_positions()
        return mapping[target.capitalize()][0]

    def _get_keys_matching_read_value(self, value):
        keys = [
            key for key, device in self._all_attached.items() if device.read() == value
        ]
        return keys

    def _get_mapped_positions(self):
        return {
            "Park all beamstops": (
                XPositions.Parked,
                ArmPositions.InBeam,
                ArmPositions.Parked,
                ArmPositions.Parked,
                ArmPositions.Parked,
                ArmPositions.Parked,
                ArmPositions.Parked,
            ),
            "Monitor": (
                XPositions.Pos1,
                ArmPositions.InBeam,
                ArmPositions.InBeam,
                ArmPositions.Parked,
                ArmPositions.Parked,
                ArmPositions.Parked,
                ArmPositions.Parked,
            ),
            "Beamstop 2": (
                XPositions.Pos2,
                ArmPositions.InBeam,
                ArmPositions.Parked,
                ArmPositions.InBeam,
                ArmPositions.Parked,
                ArmPositions.Parked,
                ArmPositions.Parked,
            ),
            "Beamstop 2 + monitor": (
                XPositions.Pos2,
                ArmPositions.InBeam,
                ArmPositions.InBeam,
                ArmPositions.InBeam,
                ArmPositions.Parked,
                ArmPositions.Parked,
                ArmPositions.Parked,
            ),
            "Beamstop 3": (
                XPositions.Pos3,
                ArmPositions.InBeam,
                ArmPositions.Parked,
                ArmPositions.Parked,
                ArmPositions.InBeam,
                ArmPositions.Parked,
                ArmPositions.Parked,
            ),
            "Beamstop 3 + monitor": (
                XPositions.Pos3,
                ArmPositions.InBeam,
                ArmPositions.InBeam,
                ArmPositions.Parked,
                ArmPositions.InBeam,
                ArmPositions.Parked,
                ArmPositions.Parked,
            ),
            "Beamstop 4": (
                XPositions.Pos4,
                ArmPositions.InBeam,
                ArmPositions.Parked,
                ArmPositions.Parked,
                ArmPositions.Parked,
                ArmPositions.InBeam,
                ArmPositions.Parked,
            ),
            "Beamstop 4 + monitor": (
                XPositions.Pos4,
                ArmPositions.InBeam,
                ArmPositions.InBeam,
                ArmPositions.Parked,
                ArmPositions.Parked,
                ArmPositions.InBeam,
                ArmPositions.Parked,
            ),
            "Beamstop 5": (
                XPositions.Pos5,
                ArmPositions.InBeam,
                ArmPositions.Parked,
                ArmPositions.Parked,
                ArmPositions.Parked,
                ArmPositions.Parked,
                ArmPositions.InBeam,
            ),
            "Beamstop 5 + monitor": (
                XPositions.Pos5,
                ArmPositions.InBeam,
                ArmPositions.InBeam,
                ArmPositions.Parked,
                ArmPositions.Parked,
                ArmPositions.Parked,
                ArmPositions.InBeam,
            ),
        }
