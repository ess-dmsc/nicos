import time

from nicos.core import Param, status
from nicos.devices.generic.virtual import VirtualTimer


class TimerChannel(VirtualTimer):
    """
    A virtual timer channel that can be used to count for a specified duration.
    """

    parameters = {
        "update_interval": Param(
            "The update interval in seconds", type=float, default=0.1
        ),
    }

    def _counting(self):
        self.log.debug("timing to %.3f", self.preselection)
        finish_at = time.time() + self.preselection - self.curvalue
        try:
            while not self._stopflag:
                if self.iscontroller and time.time() >= finish_at:
                    self.curvalue = self.preselection
                    break
                time.sleep(self.update_interval)
                self.curvalue += self.update_interval
        finally:
            self.curstatus = (status.OK, "idle")
