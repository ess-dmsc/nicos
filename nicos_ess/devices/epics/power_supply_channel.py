from nicos.core import (
    Attach,
    CanDisable,
    Override,
    Param,
    pvname,
    status,
)
from nicos.devices.abstract import MappedReadable
from nicos_ess.devices.epics.pva.epics_common import (
    EpicsDeviceBase,
    command_channel,
    readback_channel,
)


class PowerSupplyChannel(EpicsDeviceBase, CanDisable, MappedReadable):
    """Power Supply Channel class

    It can reads and control the power of a channel (enable/disable the device).
    Also, it reads its voltage, current, and status.
    """

    parameters = {
        "board": Param("Power supply board"),
        "channel": Param("Power supply channel"),
        "ps_pv": Param(
            "Power supply record PV.",
            type=pvname,
            mandatory=True,
        ),
        "voltage_monitor": Param(
            "Voltage monitor readback value",
            volatile=True,
            fmtstr="%.3f",
            # Not sure if setting internal and userparam are making a difference.
            # Setting them anyway just for readability.
            internal=True,
            userparam=True,
        ),
        "voltage_units": Param(
            "Voltage monitor readback units",
            default="V",
            type=str,
        ),
        "current_monitor": Param(
            "Current monitor readback value",
            volatile=True,
            fmtstr="%.3f",
            internal=True,
            userparam=True,
        ),
        "current_units": Param(
            "Current monitor readback units",
            default="uA",
            type=str,
        ),
    }

    parameter_overrides = {
        "unit": Override(settable=False),
    }

    valuetype = int

    _default_pv_prefix_attr = "ps_pv"
    _primary_channel = "power_rb"
    _epics_channels = {
        "voltage_monitor": readback_channel("-VMon", refresh_status=True),
        "current_monitor": readback_channel("-IMon", refresh_status=True),
        "power_rb": readback_channel("-Pw-RB", primary=True),
        "power": command_channel("-Pw"),
        "status_on": readback_channel("-Status-ON", refresh_status=True),
    }

    _connect_channels = ("voltage_monitor",)

    def _after_subscribe(self, mode):
        MappedReadable.doInit(self, mode)

    def _readRaw(self, maxage=0):
        return self._read_channel_cached("power_rb", maxage=maxage)

    def doRead(self, maxage=0):
        return self._mapReadValue(self._readRaw(maxage))

    def status_on(self):
        """Returns a simplified (bool) status."""
        return bool(self._read_channel_cached("status_on"))

    def _compute_status(self, maxage=0):
        # TODO: Check other status bit PVs for errors?

        # First part of the msg
        channel_stat_msg = "Channel is ON" if self.status_on() else "Channel is OFF"

        # Check voltage
        voltage_val = self._read_channel_cached("voltage_monitor", maxage=maxage)
        voltage_val = (
            self.fmtstr % voltage_val if isinstance(voltage_val, float) else None
        )
        # and current
        current_val = self._read_channel_cached("current_monitor", maxage=maxage)
        current_val = (
            self.fmtstr % current_val if isinstance(current_val, float) else None
        )

        # Build message
        msg = channel_stat_msg + " ({} {} / {} {})".format(
            voltage_val if voltage_val else "?",
            self.voltage_units,
            current_val if current_val else "?",
            self.current_units,
        )

        if not voltage_val or not current_val:
            return status.ERROR, msg
        return status.OK, msg

    def doEnable(self, on):
        self._epics.put_channel_value("power", 1 if on else 0)

    def doReadVoltage_Monitor(self):
        return self._epics.get_channel_value("voltage_monitor")

    def doReadCurrent_Monitor(self):
        return self._epics.get_channel_value("current_monitor")


class PowerSupplyBank(CanDisable, MappedReadable):
    """Power Supply Bank class

    A power supply bank is a set of power supply channels (attached to it).
    It can read and control the power (on/off) of all attached channels
    (enable/disable them all at once, with a single command).

    The status of the bank is the combined status of their channels:
    - A bank is on when at least one of its channels is on.
    - Otherwise, if all channels are off, them the bank is off.
    """

    attached_devices = {
        "ps_channels": Attach(
            "Power Supply channel", PowerSupplyChannel, multiple=True
        ),
    }

    parameter_overrides = {
        "mapping": Override(
            mandatory=False, settable=True, userparam=False, volatile=False
        ),
    }

    hardware_access = False
    valuetype = int

    def _readRaw(self, maxage=0):
        """Return 1 if there is at least one channel powered ON. Otherwise, return 0."""
        for ps_channel in self._attached_ps_channels:
            ps_channel_power_rbv = ps_channel.read()
            ps_channel_power_rbv_raw = ps_channel.mapping.get(ps_channel_power_rbv)
            if ps_channel_power_rbv_raw is None:
                return None
            if ps_channel_power_rbv_raw:
                return 1
        return 0

    def doRead(self, maxage=0):
        return self._mapReadValue(self._readRaw(maxage))

    def doEnable(self, on):
        """Enable/Disable all channels of this bank."""
        for ps_channel in self._attached_ps_channels:
            ps_channel.doEnable(on)

    def status_on(self):
        """Returns a simplified status.
        Returns
        -------
        status_on : bool
            Whether Bank is ON (at least one channel is on) or not.

        channels_on : int
            How many channels are ON."""

        on_channels = 0

        for ps_channel in self._attached_ps_channels:
            if ps_channel.status_on() is None:
                return None, None
            if ps_channel.status_on():
                on_channels += 1

        return on_channels > 0, on_channels

    def doStatus(self, maxage=0):
        num_of_channels = len(self._attached_ps_channels)
        channels_stat = status.OK
        bank_stat = status.OK

        # Check how many channels are on.
        _, on_channels = self.status_on()

        # Check channels state. If any is not OK, bank is on WARN.
        for ps_channel in self._attached_ps_channels:
            ch_stat, _ = ps_channel.status()
            if ch_stat != status.OK:
                channels_stat = status.WARN
                break

        # Build status msg
        if on_channels == num_of_channels:
            msg = "Bank is ON (all channels are ON)"
        elif on_channels > 0:
            msg = f"Bank is ON ({on_channels} of {num_of_channels} channels are ON)"
            bank_stat = status.BUSY
        else:
            msg = "Bank is OFF (all channels are OFF)"

        # Confirm bank status
        if channels_stat != status.OK:
            bank_stat = channels_stat

        return bank_stat, msg

    def _get_voltage_unit(self):
        unit = list(set(ch.voltage_units for ch in self._attached_ps_channels))
        if len(unit) > 1:
            self.log.error(
                "Mismatched voltage units in power supply channels, "
                "all units must be the same"
            )
        return unit[0]
