import time
from dataclasses import replace

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

    def _on_channel_update(self, update):
        if update.channel != "read":
            return
        time_stamp = time.time()
        mean_value = np.mean(update.value)
        self._cache.put(self._name, "raw_errors", update.value, time_stamp)
        super()._on_channel_update(replace(update, value=mean_value))
