from nicos.devices.generic.detector import DummyDetector as DefaultDummyDetector
from time import time


class DummyDetector(DefaultDummyDetector):
    def doRead(self, maxage=0):
        return [1]

    def doSetPreset(self, **preset):
        self._preset = preset

    def doStart(self):
        self._start = time()

    def doTime(self, preset):
        self.doSetPreset(**preset)  # okay in simmode
        return self.doEstimateTime(0) or 0

    def doEstimateTime(self, elapsed):
        return self._preset.values[0] - elapsed

    def doFinish(self):
        pass

    def doStop(self):
        pass
