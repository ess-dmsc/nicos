from nicos.core import status
from nicos_ess.devices.epics.caen_syx527 import CaenSyx527ChannelGroup


class FakeCaenSyx527ChannelGroup(CaenSyx527ChannelGroup):
    """Controllable power-supply status for tests of attached devices."""

    def doPreinit(self, mode):
        self._source_ids = tuple(self.sources)
        self.valuetype = float
        self._value = 0.0
        self._target = 0.0
        self._currents = 0.0
        self._current_limits = 0.0
        self._reported_status = status.DISABLED, "output disabled"
        self.parameters["currents"].unit = "uA"
        self.parameters["current_limits"].unit = "uA"

    def doInit(self, mode):
        pass

    @property
    def reported_status(self):
        return self._reported_status

    @reported_status.setter
    def reported_status(self, value):
        self._reported_status = value

    def doRead(self, maxage=0):
        return self._value

    def doReadTarget(self):
        return self._target

    def doReadCurrents(self):
        return self._currents

    def doReadCurrent_Limits(self):
        return self._current_limits

    def doReadUnit(self):
        return "V"

    def doStart(self, target):
        self._target = target

    def doWriteCurrent_Limits(self, value):
        self._current_limits = value
        return value

    def doEnable(self, on):
        self._reported_status = (
            (status.OK, "output enabled")
            if on
            else (status.DISABLED, "output disabled")
        )

    def doStatus(self, maxage=0):
        return self.reported_status
