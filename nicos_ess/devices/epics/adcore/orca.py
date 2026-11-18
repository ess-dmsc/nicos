"""Hamamatsu ORCA-Flash4.0 on the ESS ``ADOrca`` driver.

At ESS the EVR triggers the camera in "Sync Readout" mode. An image is exposed
between two readout edges, and ``TriggerTimes`` says how many triggers the
image spans. NICOS calls it ``numtriggers``. Exposure and period are both
``numtriggers / triggerrate``. The driver uses ``AcquireTime`` and
``AcquirePeriod`` only for its start check, which requires
``AcquirePeriod >= ReadoutTime + AcquireTime``.
"""

import math
import time

from nicos.core import Attach, InvalidValueError, Param, Readable, floatrange, oneof
from nicos_ess.devices.epics.adcore.base import (
    AreaDetector,
    adcore_setting,
    ess_setting,
    reader,
    setting_methods,
)
from nicos_ess.devices.epics.pva.epics_common import EpicsEnumParam, readback_channel

# doPrepare writes these trigger settings and the polarity.
SYNC_READOUT = {
    "TriggerSource": "External",
    "TriggerMode": "Normal",
    "TriggerActive": "Sync Readout",
    "TriggerGlobalExposure": "Delayed",
    "TriggerConnector": "BNC",
}


class OrcaFlash4(AreaDetector):
    """Hamamatsu ORCA-Flash4.0 V3 C13440-20CU, triggered by the EVR in Sync Readout."""

    parameters = {
        "triggerrate": Param(
            "Rate of the EVR triggers. It is 14 Hz for event 16 (NiSync) and the "
            "beam rate for event 17, which marks the intended pulses on target",
            type=floatrange(1e-3),
            default=14.0,
            unit="Hz",
            settable=True,
            category="general",
        ),
        "triggerpolarity": Param(
            "Active edge of the EVR trigger as wired to the camera",
            type=oneof("Negative", "Positive"),
            default="Positive",
        ),
        "binning": Param(
            "On-chip binning",
            type=EpicsEnumParam("binning_rbv"),
            settable=True,
            volatile=True,
            category="general",
        ),
        "cooling": Param(
            "Sensor cooler mode",
            type=EpicsEnumParam("cooling_rbv"),
            settable=True,
            volatile=True,
            category="general",
        ),
        "temperature": Param(
            "Sensor temperature",
            type=float,
            unit="degC",
            volatile=True,
            category="general",
        ),
        "coolerstatus": Param("Sensor cooler status", type=str, volatile=True),
        "framerate": Param(
            "Frame rate measured by the driver", type=float, unit="Hz", volatile=True
        ),
        "numtriggers": Param(
            "Number of EVR triggers that one image spans, set as TriggerTimes. "
            "Exposure and period are both numtriggers / triggerrate",
            type=int,
            settable=True,
            volatile=True,
            category="general",
        ),
    }

    attached_devices = {
        "watercooler": Attach(
            "Chiller of the camera. Sensor cooling cannot be switched on while "
            "the chiller is off",
            Readable,
            optional=True,
        ),
    }

    # A cache key must hold the value that the parameter of the same name reads.
    # The acquiretime and acquireperiod parameters are computed from the
    # triggers, so AcquireTime and AcquirePeriod get no cache key. The trigger
    # settings get none because they are not parameters.
    _epics_channels = {
        **AreaDetector._epics_channels,
        **adcore_setting("acquiretime", "AcquireTime", cached=False),
        **adcore_setting("acquireperiod", "AcquirePeriod", cached=False),
        **{
            name: info
            for record in (*SYNC_READOUT, "TriggerPolarity")
            for name, info in ess_setting(
                record, record, is_enum=True, cached=False
            ).items()
        },
        **ess_setting("numtriggers", "TriggerTimes"),
        **ess_setting("binning", "Binning", is_enum=True),
        **ess_setting("cooling", "SensorCooler", is_enum=True),
        "temperature": readback_channel("Temperature-R", cache_key="temperature"),
        "cooler_status": readback_channel(
            "CoolerStatus-R", cache_key="coolerstatus", is_enum=True
        ),
        "frame_rate": readback_channel("FrameRate-R", cache_key=None, subscribe=False),
    }

    def doPrepare(self):
        """Put the camera in EVR Sync Readout and write only settings that differ."""
        wanted = {**SYNC_READOUT, "TriggerPolarity": self.triggerpolarity}
        for record, choice in wanted.items():
            if self._epics.get_channel_value(f"{record}_rbv") != choice:
                self.log.debug("setting %s to %s", record, choice)
                self._put_setting(record, choice)
        AreaDetector.doPrepare(self)

    def _on_channel_update(self, update):
        if update.channel == "numtriggers_rbv":
            self._cache_exposure(update.value / self.triggerrate)
        AreaDetector._on_channel_update(self, update)

    def _cache_exposure(self, seconds):
        # Exposure and period are computed from the triggers and the trigger
        # rate, so no IOC update refreshes their cache keys.
        now = time.time()
        self._cache.put(self._name, "acquiretime", seconds, now)
        self._cache.put(self._name, "acquireperiod", seconds, now)

    doReadNumtriggers = reader("numtriggers_rbv")

    def doWriteTriggerrate(self, value):
        self._cache_exposure(self.numtriggers / value)

    def doWriteNumtriggers(self, value):
        if value < 1:
            raise InvalidValueError(self, "an image spans at least one trigger")
        self._put_setting("numtriggers", value)

    def doReadAcquiretime(self):
        return self.numtriggers / self.triggerrate

    def doReadAcquireperiod(self):
        # In Sync Readout the edge that ends one image starts the next one.
        return self.numtriggers / self.triggerrate

    def doWriteAcquiretime(self, value):
        self.numtriggers = self._triggers_for("acquiretime", value)

    def doWriteAcquireperiod(self, value):
        self.numtriggers = self._triggers_for("acquireperiod", value)

    def _triggers_for(self, param, value):
        """Return the whole number of triggers closest to *value* in seconds."""
        triggers = round(value * self.triggerrate)
        if triggers < 1:
            raise InvalidValueError(
                self,
                f"an image spans at least one trigger, which is "
                f"{1 / self.triggerrate:.4g} s at {self.triggerrate} Hz",
            )
        exposure = triggers / self.triggerrate
        if not math.isclose(exposure, value, rel_tol=1e-6):
            self.log.warning(
                "%s is set in whole triggers on this camera, so it was rounded "
                "to %d triggers, which is %.4g s at %g Hz",
                param,
                triggers,
                exposure,
                self.triggerrate,
            )
        return triggers

    doReadBinning, doWriteBinning = setting_methods("binning")
    doReadTemperature = reader("temperature")
    doReadCoolerstatus = reader("cooler_status")
    doReadFramerate = reader("frame_rate")
    doReadCooling = reader("cooling_rbv")

    def doWriteCooling(self, value):
        chiller = self._attached_watercooler
        if (
            value != "Off"
            and chiller is not None
            and str(chiller.read(0)).upper() == "OFF"
        ):
            raise InvalidValueError(
                self, f"cannot set cooling to {value!r} while {chiller} is off"
            )
        self._put_setting("cooling", value)
