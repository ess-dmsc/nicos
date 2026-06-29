from nicos.core import (
    SIMULATION,
    Attach,
    InvalidValueError,
    Override,
    Param,
    oneof,
    pvname,
    status,
    usermethod,
)
from nicos.devices.abstract import MappedMoveable
from nicos_ess.devices.epics.pva import EpicsMappedReadable
from nicos_ess.devices.epics.pva.epics_common import (
    EpicsDeviceBase,
    command_channel,
    readback_channel,
)

# EPICS status enum order:
# [Infusing, Withdrawing, Stopped, Paused, "Pause phase", "Trigger wait",
#  Purging, Unknown]

CHOICES_STATUS_MAP = {
    "Infusing": status.BUSY,
    "Withdrawing": status.BUSY,
    "Stopped": status.OK,
    "Paused": status.OK,
    "Pause phase": status.BUSY,
    "Trigger wait": status.BUSY,
    "Purging": status.BUSY,
    "Unknown": status.UNKNOWN,
}


class SyringePumpController(EpicsDeviceBase, MappedMoveable):
    """
    A device for controlling the NE1002 and NE1600 syringe pumps.

    The device:
      - exposes the mapped commands: start / stop / purge / pause / resume
      - reads the current textual *state* from the attached `status` device
      - reads error text from `message_pv` (non-empty => ERROR)
      - writes to start/stop/purge/pause PVs
    """

    parameters = {
        "start_pv": Param(
            "PV for starting the device", type=pvname, mandatory=True, userparam=False
        ),
        "stop_pv": Param(
            "PV for stopping the device", type=pvname, mandatory=True, userparam=False
        ),
        "purge_pv": Param(
            "PV for purging the device", type=pvname, mandatory=True, userparam=False
        ),
        "pause_pv": Param(
            "PV for pausing and resuming the device",
            type=pvname,
            mandatory=True,
            userparam=False,
        ),
        "message_pv": Param(
            "PV for reading error messages from the device",
            type=pvname,
            mandatory=True,
            userparam=False,
        ),
    }

    parameter_overrides = {
        "unit": Override(mandatory=False, settable=False, userparam=False),
        "mapping": Override(mandatory=False, userparam=False, volatile=True),
    }

    attached_devices = {
        "status": Attach("Status of device", EpicsMappedReadable),
    }

    _primary_channel = "message"
    _epics_channels = {
        "message": readback_channel(
            "",
            cache_key="message",
            primary=True,
            as_string=True,
            pv_name_attr="message_pv",
        ),
        "start": command_channel("", pv_name_attr="start_pv"),
        "stop": command_channel("", pv_name_attr="stop_pv"),
        "purge": command_channel("", pv_name_attr="purge_pv"),
        "pause": command_channel("", pv_name_attr="pause_pv"),
    }

    def doPreinit(self, mode):
        self._commands = {
            "start": self.start_pump,
            "stop": self.stop_pump,
            "purge": self.purge,
            "pause": self.pause_pump,
            "resume": self.resume_pump,
        }
        EpicsDeviceBase.doPreinit(self, mode)

    def _after_subscribe(self, mode):
        self._setROParam(
            "mapping", {cmd: i for i, cmd in enumerate(self._commands.keys())}
        )
        MappedMoveable.doInit(self, mode)
        self.valuetype = oneof(*self._commands.keys())

    def doStart(self, target):
        if target in self._commands:
            self._commands[target]()

    def doStop(self):
        self.stop_pump()

    def doRead(self, maxage=0):
        return self._attached_status.read(maxage)

    def doReadMapping(self):
        return {cmd: i for i, cmd in enumerate(self._commands.keys())}

    def _compute_status(self, maxage=0):
        if self._mode == SIMULATION:
            return status.OK, ""

        # Non-empty error message => ERROR with message
        try:
            device_msg = self._read_channel_cached("message", maxage=maxage) or ""
        except Exception:
            # If we can't read the message PV, signal comms issue
            return status.ERROR, "communication failure (reading message PV)"

        if device_msg.strip():
            return status.ERROR, device_msg

        try:
            attached_message = self._attached_status.read(0)
            if attached_message not in CHOICES_STATUS_MAP:
                return status.UNKNOWN, f"unknown device state: {attached_message}"
            return CHOICES_STATUS_MAP[attached_message], attached_message
        except Exception:
            return status.ERROR, "communication failure (reading status device)"

    @usermethod
    def start_pump(self):
        """Start pumping"""
        if self._mode == SIMULATION:
            return
        curr_state = self._attached_status.read(0)
        if curr_state != "Stopped":
            raise InvalidValueError(
                "Cannot start from the current state, please stop the pump first"
            )
        self._epics.put_channel_value("start", 1)

    @usermethod
    def stop_pump(self):
        """Stop pumping"""
        if self._mode == SIMULATION:
            return
        curr_state = self._attached_status.read(0)
        if curr_state == "Stopped":
            self.log.warning("Stop request ignored as pump already stopped")
            return
        self._epics.put_channel_value("stop", 2)

    @usermethod
    def purge(self):
        """Purge the pump"""
        if self._mode == SIMULATION:
            return
        curr_state = self._attached_status.read(0)
        if curr_state != "Stopped":
            raise InvalidValueError(
                "Cannot purge from the current state, please stop the pump first"
            )
        self._epics.put_channel_value("purge", 3)

    @usermethod
    def pause_pump(self):
        """Pause pumping"""
        if self._mode == SIMULATION:
            return
        curr_state = self._attached_status.read(0)
        if curr_state not in ["Infusing", "Withdrawing"]:
            raise InvalidValueError(
                f"Cannot pause from the current state ({curr_state})"
            )
        self._epics.put_channel_value("pause", 4)

    @usermethod
    def resume_pump(self):
        """Resume pumping"""
        if self._mode == SIMULATION:
            return
        curr_state = self._attached_status.read(0)
        if curr_state != "Paused":
            self.log.warning("Resume request ignored as pump is not paused")
            return
        self._epics.put_channel_value("pause", 5)
