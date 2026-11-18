"""TimePix3 camera on ADTimePix3 with the ESS EMPIR event processing.

Every acquisition writes its raw ``.tpx3`` files into a new folder, and then
EMPIR is told to process that folder. The IOC expects this start sequence.

1. In prepare, ``RawFilePath`` is set to the new folder, ``WriteData`` makes
   SERVAL use it, and ``TSReady`` is cleared.
2. The acquisition is started and NICOS waits for ``TSReady``, which the IOC
   sets when the first trigger arrives.
3. ``PathToAdd`` hands the folder to EMPIR, which echoes it in
   ``PathLastAdded`` once the folder is queued.
"""

import time

from nicos.core import CommunicationError, Param
from nicos_ess.devices.epics.adcore.base import (
    AreaDetector,
    adcore_setting,
    reader,
    setting_channels,
    setting_methods,
)
from nicos_ess.devices.epics.pva.epics_common import (
    readback_channel,
    setpoint_channel,
)


def _chars(text):
    """Return *text* as a CHAR waveform value with a terminating null."""
    return list(text.encode()) + [0]


def _text(value):
    return bytes(int(char) for char in value).decode(errors="ignore").rstrip("\x00")


class TimepixDetector(AreaDetector):
    """TimePix3 camera whose raw data EMPIR turns into images."""

    parameters = {
        "rawdir": Param(
            "Folder URL that SERVAL writes the raw files under. Each acquisition "
            "gets its own subfolder",
            type=str,
            default="file:/data",
        ),
        "threshold_fine": Param(
            "Chip 0 fine threshold (DAC units)",
            type=int,
            settable=True,
            volatile=True,
            category="general",
        ),
        "threshold_coarse": Param(
            "Chip 0 coarse threshold (DAC units)",
            type=int,
            settable=True,
            volatile=True,
            category="general",
        ),
        "min_photons": Param(
            "Minimum number of photons for an event to count as a neutron",
            type=float,
            settable=True,
            volatile=True,
            category="general",
        ),
        "min_psd": Param(
            "Minimum pulse shape discrimination value for a neutron",
            type=float,
            settable=True,
            volatile=True,
            category="general",
        ),
        "nprocessing": Param(
            "Raw files queued for EMPIR processing", type=int, volatile=True
        ),
    }

    _epics_channels = {
        **AreaDetector._epics_channels,
        **adcore_setting("threshold_fine", "CHIP0_Vth_fine"),
        **adcore_setting("threshold_coarse", "CHIP0_Vth_coarse"),
        # The EMPIR filter records have no separate readback record.
        **setting_channels("min_photons", "EvFlit_PhMin", "EvFlit_PhMin"),
        **setting_channels("min_psd", "EvFlit_PsdMin", "EvFlit_PsdMin"),
        "num_processing": readback_channel("N_Processing", cache_key="nprocessing"),
        "raw_file_path": setpoint_channel(
            "RawFilePath", cache_key=None, subscribe=False
        ),
        "write_data": setpoint_channel("WriteData", cache_key=None, subscribe=False),
        "ts_ready": setpoint_channel("TSReady", cache_key=None, subscribe=False),
        "path_to_add": setpoint_channel("PathToAdd", cache_key=None, subscribe=False),
        "path_last_added": readback_channel(
            "PathLastAdded", cache_key=None, subscribe=False
        ),
    }

    doReadThreshold_Fine, doWriteThreshold_Fine = setting_methods("threshold_fine")
    doReadThreshold_Coarse, doWriteThreshold_Coarse = setting_methods(
        "threshold_coarse"
    )
    doReadMin_Photons, doWriteMin_Photons = setting_methods("min_photons")
    doReadMin_Psd, doWriteMin_Psd = setting_methods("min_psd")
    doReadNprocessing = reader("num_processing")

    def doPrepare(self):
        """Do step 1 before any detector of the count starts.

        If the IOC refuses, the count fails before anything was started.
        """
        AreaDetector.doPrepare(self)
        self._folder = f"raw_tpx_{time.time_ns()}"
        try:
            self._epics.put_channel_value(
                "raw_file_path", _chars(f"{self.rawdir}/{self._folder}")
            )
            self._epics.put_channel_value("write_data", 1)
            self._epics.put_channel_value("ts_ready", 0)
        except Exception:
            self._leave_idle()
            raise

    def doStart(self):
        try:
            AreaDetector.doStart(self)
            self._wait("ts_ready", lambda value: value == 1, "the first trigger")
            self._epics.put_channel_value("path_to_add", _chars(self._folder))
            self._wait(
                "path_last_added",
                lambda value: _text(value) == self._folder,
                f"EMPIR to queue {self._folder}",
            )
        except Exception:
            self._leave_idle()
            raise

    def _leave_idle(self):
        """Leave the camera idle and not writing after a failed start."""
        self._setROParam("counting", False)
        for channel in ("acquire", "write_data"):
            try:
                self._epics.put_channel_value(channel, 0)
            except Exception as err:
                self.log.warning(
                    "cannot reset %s after the failed start: %s", channel, err
                )

    def _wait(self, channel, done, what):
        try:
            self._epics.wait_for(channel, done, timeout=self.starttimeout)
        except CommunicationError:
            raise CommunicationError(
                self, f"timed out after {self.starttimeout} s waiting for {what}"
            ) from None
