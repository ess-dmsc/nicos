import re

from nicos.core import Param
from nicos.core.utils import waitForCompletion
from nicos_ess.devices.mapped_controller import MultiTargetMapping


class LokiBeamstopController(MultiTargetMapping):
    parameters = {
        "all_parked_mapping": Param(
            mandatory=True,
            settable=True,
            description="The mapped value that corresponds to all motors parked",
            type=str,
        )
    }

    def doStart(self, value):
        active_beamstop = self._get_beamstop_number(self.read())
        requested_beamstop = self._get_beamstop_number(value)
        if requested_beamstop != active_beamstop:
            self._park_beamstops()
        self._engage_beamstop(value)

    def _get_beamstop_number(self, value):
        active_beamstop_match = re.match(r"(Beamstop \d|Park)", value)
        if active_beamstop_match:
            return active_beamstop_match.group()
        else:
            return "None"

    def _park_beamstops(self):
        devices, targets = self._park_sequence()
        self._move_to_targets(devices, targets)

    def _engage_beamstop(self, value):
        devices, targets = self._beamstop_sequence(value)
        self._move_to_targets(devices, targets)

    def _move_to_targets(self, devices, targets):
        for device, target in zip(devices, targets):
            device.start(target)
            waitForCompletion(device)

    def _park_sequence(self):
        devices = self._attached_controlled_devices
        targets = self.mapping.get(self.all_parked_mapping, None)
        return devices, targets

    def _beamstop_sequence(self, value):
        devices_reversed = self._attached_controlled_devices[::-1]
        targets = self.mapping.get(value, None)
        if targets:
            targets_reversed = targets[::-1]
        else:
            targets_reversed = targets
        return devices_reversed, targets_reversed
