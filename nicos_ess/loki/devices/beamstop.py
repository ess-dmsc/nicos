from typing import List, Tuple

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
from nicos.devices.generic.sequence import SeqCall, SeqDev, SeqSleep, SequencerMixin
from nicos.utils import num_sort
from nicos_ess.devices.mapped_controller import MappedController


class LokiBeamstopArmPositioner(MappedController):
    def doInit(self, mode):
        MappedController.doInit(self, mode)

    def doWriteMapping(self, mapping):
        if sorted(mapping.keys()) != ["In beam", "Parked", "Intermediate"]:
            raise ConfigurationError(
                "Only 'In beam', 'Parked' and 'Intermediate' are allowed as mapped positions"
            )
        for position in mapping.values():
            self._check_limits(position)
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
        if "Parked" in self.mapping.keys() and value > self.mapping["Parked"]:
            return "Above park position"
        if "in beam" in self.mapping.keys() and value < self.mapping["In beam"]:
            return "Below in-beam position"
        return "In between"

    def _check_limits(self, position):
        limits = self._attached_controlled_device.userlimits
        is_allowed, reason = self._attached_controlled_device.isAllowed(position)
        if not is_allowed:
            raise LimitError(
                f"Mapped position ({position}) outside user limits {limits}"
            )


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
        MappedMoveable.doInit(self, mode)
        self.valuetype = oneof(*self._get_mapped_positions().keys())

    def doRead(self, maxage=0):
        return self._mapReadValue(self._readRaw(maxage))

    def _readRaw(self, maxage=0):
        return tuple(channel.read(maxage) for channel in self._all_attached.values())

    def _mapReadValue(self, value):
        inverse_mapping = {v: k for k, v in self._full_mapping.items()}
        mapped_value = inverse_mapping.get(value, None)
        if not mapped_value:
            return "In Between"
        return mapped_value

    def doReadMapping(self):
        return self._get_mapped_positions()

    def doStart(self, target):
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
        self._startSequence(sequence)

    def _generateSequence(self, target):
        devices_in_park = self._get_keys_matching_device_read_value("Parked")

        if "park" in target.lower():
            devices_not_parked = list(
                set(self._all_attached.keys()) - set(devices_in_park)
            )
            seq = self._park_sequence(devices_not_parked)
            return seq

        request_in_beam = [arm.strip().lower() for arm in target.split("+")]
        devices_in_beam = self._get_keys_matching_device_read_value("In beam")
        move_to_in_beam = list(set(request_in_beam) - set(devices_in_beam))
        move_to_park = list(
            set(self._all_attached.keys()) - set(devices_in_park) - set(request_in_beam)
        )
        x_pos = self._get_x_pos(target)

        seq = []
        if len(move_to_park) > 0:
            seq.extend(self._park_sequence(move_to_park))
        if len(move_to_in_beam) > 0:
            seq.extend(self._in_beam_sequence(move_to_in_beam))
        if self._all_attached["y"].read != "In beam":
            seq.append(SeqDev(self._all_attached["y"], "In beam"))
        if self._all_attached["x"].read != x_pos:
            seq.append(SeqDev(self._all_attached["x"], x_pos))
        return seq

    def _get_x_pos(self, target):
        mapping = self._get_mapped_positions()
        return mapping[target][0]

    def _park_sequence(self, devices: List[str]) -> List[Tuple[SeqDev, ...]]:
        """
        Build the parking sequence.

        The sequence first moves the beamstops away from the detector,
        then raises the arms to their parked positions.

        Args:
            devices
                Key of devices corresponding to the dict of attached devices

        Returns:
            Ordered execution steps. Each list element represents
            one execution stage:
                - A single-element tuple → sequential step
                - A multi-element tuple → parallel step
        """
        seq = []
        if "x" in devices:
            seq.append(SeqDev(self._all_attached["x"], "Parked"))
        arms_devices = [key for key in devices if "beamstop" in key or "monitor" in key]
        if arms_devices:
            seq.append(
                tuple(
                    SeqDev(device, "Parked")
                    for key, device in self._all_attached.items()
                    if key in arms_devices
                )
            )
        return seq

    def _in_beam_sequence(self, devices: List[str]) -> List[Tuple[SeqDev, ...]]:
        """
        Build the sequence for adding a beamstop to the beam.

        The sequence first moves the beamstops down into the beam,
        then moves the beamstop into the center of the beam and
        finally moves the beamstops towards the detector.

        Args:
            devices
                Key of devices corresponding to the dict of attached devices

        Returns:
            Ordered execution steps. Each list element represents
            one execution stage:
                - A single-element tuple → sequential step
                - A multi-element tuple → parallel step
        """
        seq = []
        beamstop = self._get_device_matching_substring(devices, "beamstop")
        monitor = self._get_device_matching_substring(devices, "monitor")

        if monitor and beamstop:
            print("in if block")
            # beamstop needs to lower slightly first for twincat to update limits
            seq.extend(
                [
                    SeqDev(beamstop, "Intermediate"),
                    SeqSleep(10),
                ]
            )

        seq.append(
            tuple(SeqDev(device, "In beam") for device in (beamstop, monitor) if device)
        )
        return seq

    def _get_device_matching_substring(self, devices, search_key):
        for key in devices:
            if search_key in key:
                return self._all_attached[key]
        return None

    def _get_keys_matching_device_read_value(self, value):
        keys = [
            key for key, device in self._all_attached.items() if device.read() == value
        ]
        return keys

    def _get_mapped_positions(self):
        return {
            "Park all beamstops": (
                "Parked",
                "In beam",
                "Parked",
                "Parked",
                "Parked",
                "Parked",
                "Parked",
            ),
            "Monitor": (
                "Xpos BS1",
                "In beam",
                "In beam",
                "Parked",
                "Parked",
                "Parked",
                "Parked",
            ),
            "Beamstop 2": (
                "Xpos BS2",
                "In beam",
                "Parked",
                "In beam",
                "Parked",
                "Parked",
                "Parked",
            ),
            "Beamstop 2 + monitor": (
                "Xpos BS2",
                "In beam",
                "In beam",
                "In beam",
                "Parked",
                "Parked",
                "Parked",
            ),
            "Beamstop 3": (
                "Xpos BS3",
                "In beam",
                "Parked",
                "Parked",
                "In beam",
                "Parked",
                "Parked",
            ),
            "Beamstop 3 + monitor": (
                "Xpos BS3",
                "In beam",
                "In beam",
                "Parked",
                "In beam",
                "Parked",
                "Parked",
            ),
            "Beamstop 4": (
                "Xpos BS4",
                "In beam",
                "Parked",
                "Parked",
                "Parked",
                "In beam",
                "Parked",
            ),
            "Beamstop 4 + monitor": (
                "Xpos BS4",
                "In beam",
                "In beam",
                "Parked",
                "Parked",
                "In beam",
                "Parked",
            ),
            "Beamstop 5": (
                "Xpos BS5",
                "In beam",
                "Parked",
                "Parked",
                "Parked",
                "Parked",
                "In beam",
            ),
            "Beamstop 5 + monitor": (
                "Xpos BS5",
                "In beam",
                "In beam",
                "Parked",
                "Parked",
                "Parked",
                "In beam",
            ),
        }
