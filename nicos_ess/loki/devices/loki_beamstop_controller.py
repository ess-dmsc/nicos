import re

from nicos.core.utils import waitForCompletion
from nicos_ess.devices.mapped_controller import MultiTargetMapping


class LokiBeamstopController(MultiTargetMapping):
    def doStart(self, value):
        active_beamstop = self._get_active_beamstop()
        if not (active_beamstop in value):
            self._park_all_beamstops()
        self._move_beamstops_to_new_target(value)

    def _get_active_beamstop(self):
        cur_value = self.doRead()
        active_beamstop_match = re.match(r"Beamstop \d", cur_value)
        if active_beamstop_match:
            return active_beamstop_match.group()
        else:
            return "None"

    def _park_all_beamstops(self):
        targets = self.mapping.get(self.default_target, None)
        for channel, target in zip(self._attached_controlled_devices, targets):
            channel.start(target)
            waitForCompletion(channel)

    def _move_beamstops_to_new_target(self, value):
        targets = self.mapping.get(value, None)
        for channel, target in zip(self._attached_controlled_devices, targets):
            channel.doStart(target)
            waitForCompletion(channel)
