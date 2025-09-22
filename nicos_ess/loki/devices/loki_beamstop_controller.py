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
        active_beamstop = self._extract_beamstop_number(self.read())
        requested_beamstop = self._extract_beamstop_number(value)
        if requested_beamstop != active_beamstop:
            self.park_all_beamstops()
        self._move_beamstops(value)

    def park_all_beamstops(self):
        targets = self.mapping.get(self.all_parked_mapping, None)
        self._move_to_targets(targets)

    def _extract_beamstop_number(self, value):
        active_beamstop_match = re.match(r"Beamstop \d", value)
        if active_beamstop_match:
            return active_beamstop_match.group()
        else:
            return "None"

    def _move_beamstops(self, value):
        targets = self.mapping.get(value, None)
        self._move_to_targets(targets)

    def _move_to_targets(self, targets):
        for device, target in zip(self._attached_controlled_devices, targets):
            device.start(target)
            waitForCompletion(device)
