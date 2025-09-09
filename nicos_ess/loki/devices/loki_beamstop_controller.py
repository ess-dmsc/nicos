import re

from nicos.core.utils import waitForCompletion
from nicos_ess.devices.mapped_controller import MultiTargetMapping


class LokiBeamstopController(MultiTargetMapping):
    def doStart(self, value):
        active_beamstop = self._get_active_beamstop()
        if not (active_beamstop in value):
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

    def _get_active_beamstop(self):
        cur_value = self.read()
        active_beamstop_match = re.match(r"Beamstop \d", cur_value)
        if active_beamstop_match:
            return active_beamstop_match.group()
        else:
            return "None"
