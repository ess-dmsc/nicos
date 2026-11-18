import time

from nicos.core import MASTER, Param, status
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

    def doInit(self, mode):
        VirtualTimer.doInit(self, mode)
        if mode == MASTER:
            # A daemon that died during a count leaves BUSY in the cache.
            self.curstatus = (status.OK, "idle")

    def doPrepare(self):
        self.curvalue = 0

    def _counting(self):
        self.log.debug("timing to %.3f", self.preselection)
        start_time = time.time() - self.curvalue

        try:
            while not self._stopflag:
                now = time.time()
                elapsed = now - start_time
                if self.iscontroller and elapsed >= self.preselection:
                    self.curvalue = self.preselection
                    break

                self.curvalue = elapsed
                time.sleep(self.update_interval)
        finally:
            self.curstatus = (status.OK, "idle")
