from nicos import session
from nicos.core import SIMULATION
from nicos.devices.datasinks.scan import (
    ConsoleScanSink as BaseConsoleScanSink,
    ConsoleScanSinkHandler as BaseConsoleScanSinkHandler,
)


class ConsoleScanSinkHandler(BaseConsoleScanSinkHandler):
    def prepare(self):
        if session.mode != SIMULATION:
            self.manager.assignCounter(self.dataset)


class ConsoleScanSink(BaseConsoleScanSink):
    """A DataSink that prints scan data onto the console."""

    handlerclass = ConsoleScanSinkHandler
