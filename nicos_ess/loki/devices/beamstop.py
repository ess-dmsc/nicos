import re

from nicos.core import (
    SIMULATION,
    Attach,
    ConfigurationError,
    HasPrecision,
    LimitError,
    MoveError,
    oneof,
)
from nicos.devices.abstract import MappedMoveable
from nicos.devices.generic.sequence import SeqDev, SequencerMixin
from nicos.utils import num_sort
from nicos_ess.devices.mapped_controller import MappedController


class LokiBeamstopArmPositioner(MappedController):
    def doInit(self, mode):
        MappedController.doInit(self, mode)

    def doWriteMapping(self, mapping):
        if sorted(mapping.keys()) != ["In beam", "Parked"]:
            raise ConfigurationError(
                "Only 'In beam' and 'Parked' are allowed as mapped positions"
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
        else:
            if value > self.mapping["Parked"]:
                return "Above park position"
            elif value < self.mapping["In beam"]:
                return "Below in-beam position"
            else:
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

    def doPreinit(self, mode):
        self._all_attached = [
            self._attached_bsx_positioner,
            self._attached_bsy_positioner,
            self._attached_bs1_positioner,
            self._attached_bs2_positioner,
            self._attached_bs3_positioner,
            self._attached_bs4_positioner,
            self._attached_bs5_positioner,
        ]
        self._full_mapping = self._get_mapped_positions()

    def doRead(self, maxage=0):
        return self._mapReadValue(self._readRaw(maxage))

    def _readRaw(self, maxage=0):
        return tuple(channel.read(maxage) for channel in self._all_attached)

    def _mapReadValue(self, value):
        inverse_mapping = {v: k for k, v in self._full_mapping.items()}
        mapped_value = inverse_mapping.get(value, None)
        if not mapped_value:
            return "In Between"
        return mapped_value

    def doStart(self, target):
        """
        Generate and start a sequence if non is running.
        Just calls ``self._startSequence(self._generateSequence(target))``
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
        self._startSequence(self._generateSequence(target))

    def _generateSequence(self, target):
        active_beamstop = self._get_beamstop_number(self.read())
        requested_beamstop = self._get_beamstop_number(target)
        seq = []
        if requested_beamstop != active_beamstop:
            seq.extend(self._park_sequence())
        seq.extend(self._beamstop_sequence(target))
        return seq

    def _get_beamstop_number(self, value):
        active_beamstop_match = re.match(r"(Beamstop \d|Park)", value)
        if active_beamstop_match:
            return active_beamstop_match.group()
        else:
            return "None"

    def _park_sequence(self):
        """
        Parking sequence: x to park, y to in-beam, z-arms to park
        """
        targets = self._full_mapping.get("Park all beamstops", None)
        seq = []
        seq.append(SeqDev(self._all_attached[0], targets[0]))
        seq.append(SeqDev(self._all_attached[1], targets[1]))
        seq.append(
            tuple(
                SeqDev(dev, tar)
                for dev, tar in zip(self._all_attached[2:], targets[2:])
            )
        )
        return seq

    def _beamstop_sequence(self, target):
        """
        Engage beamstop sequence: z-arms to in-beam, y to in-beam, x to specified beamstop position
        """
        targets = self._full_mapping.get(target, None)
        seq = []
        seq.append(
            tuple(
                SeqDev(dev, tar)
                for dev, tar in zip(self._all_attached[2:], targets[2:])
            )
        )
        seq.append(SeqDev(self._all_attached[1], targets[1]))
        seq.append(SeqDev(self._all_attached[0], targets[0]))
        return seq

    def _get_mapped_positions(self):
        full_mapping = {
            "Park all beamstops": (
                "Parked",
                "In beam",
                "Parked",
                "Parked",
                "Parked",
                "Parked",
                "Parked",
            ),
            "Beamstop 1": (
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
        return full_mapping
