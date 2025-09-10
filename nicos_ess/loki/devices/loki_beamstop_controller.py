import re

from nicos.core.utils import waitForCompletion
from nicos_ess.devices.mapped_controller import MultiTargetMapping


class LokiBeamstopController(MultiTargetMapping):
    def doStart(self, value):
        active_beamstop = self._extract_beamstop_number(self.read())
        requested_beamstop = self._extract_beamstop_number(value)
        if requested_beamstop != active_beamstop:
            self.park_all_beamstops()
        self._move_beamstops(value)

    def park_all_beamstops(self):
        """
        The default target mapping must be parking positions for all beamstop motors.
        """
        targets = self.mapping.get(self.default_target, None)
        self._move_to_targets(targets)

    def _move_beamstops(self, value):
        targets = self.mapping.get(value, None)
        self._move_to_targets(targets)

    def _move_to_targets(self, targets):
        for device, target in zip(self._attached_controlled_devices, targets):
            device.start(target)
            waitForCompletion(device)

    def _extract_beamstop_number(self, value):
        active_beamstop_match = re.match(r"Beamstop \d", value)
        if active_beamstop_match:
            return active_beamstop_match.group()
        else:
            return "None"
