import time

import numpy as np

from nicos.core import Param
from nicos_ess.devices.epics.pva import EpicsReadable


class ChopperDelayError(EpicsReadable):
    """
    A device for reading the chopper delay error. We don't want to display the
    raw values to the user, so we will calculate the mean and display that.
    """

    parameters = {
        "raw_errors": Param(
            "The raw error values.", type=list, mandatory=False, settable=True
        ),
    }

    def _value_change_callback(
        self, name, param, value, units, limits, severity, message, **kwargs
    ):
        if name != self.readpv:
            # Unexpected updates ignored
            return
        time_stamp = time.time()
        mean_value = np.mean(value)
        self._cache.put(self._name, "value", mean_value, time_stamp)
        self._cache.put(self._name, "raw_errors", value, time_stamp)
