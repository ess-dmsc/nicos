# EPICS device integration guide

This guide covers the channel-based devices in `nicos_ess.devices.epics.pva`.

A logical channel is the name used in device code, such as `readback`,
`setpoint`, or `error`. The channel table maps that name to an EPICS PV. For a
record or device with one PV root, configure the root once and declare the PV
suffixes in the channel table.

## Terminology

- `IOC`: the EPICS server process that hosts PVs.
- `record`: an object in an IOC database. A motor record is one example.
- `field`: one value belonging to a record, such as `.VAL`, `.RBV`, or
  `.PREC`. A record can expose several fields as PVs.
- `PV`: a process variable addressed by its full EPICS name, such as
  `SIM:MOTOR.RBV`.
- `PV root`: the configured part shared by several PV names. It can be a
  record name or a device prefix.
- `suffix`: the text appended to a PV root. It can be a record field such as
  `.RBV` or an ending such as `Temperature-R`.
- `readback`: the value currently reported by the IOC.
- `setpoint`: the value requested from the IOC.
- `cache key`: the name used to store a channel value in the NICOS cache.
- `logical channel`: a name used by the device class, such as `readback`,
  `setpoint`, `message`, or `error`. The channel table maps it to a PV.

The name `channel` describes the role used by the NICOS device without
assuming that the PV is a record field. A channel can use the default PV root,
another root, or a parameter containing a full PV name. In this guide,
`channel` means a logical channel-table entry, not a Channel Access connection.

## Start with an existing class

Use an existing class when the IOC contract matches one of these cases:

- `EpicsReadable`: one read PV.
- `EpicsNumericReadable`: one numeric read PV with optional `.PREC` metadata.
- `EpicsStringReadable`: one string or character-waveform read PV.
- `EpicsAnalogMoveable`: float readback and setpoint PVs.
- `EpicsDigitalMoveable`: integer readback and setpoint PVs.
- `EpicsStringMoveable`: string readback and setpoint PVs.
- `EpicsMappedReadable`: EPICS enum readback.
- `EpicsMappedMoveable`: EPICS enum readback and setpoint.
- `EpicsManualMappedAnalogMoveable`: mapping configured in the NICOS setup.

For example:

```python
devices = dict(
    temperature=device(
        "nicos_ess.devices.epics.pva.EpicsNumericReadable",
        description="Sample temperature",
        readpv="SIM:TEMP:Temperature-R",
        use_prec=False,
    ),
    setpoint=device(
        "nicos_ess.devices.epics.pva.EpicsAnalogMoveable",
        description="Sample temperature setpoint",
        readpv="SIM:TEMP:Temperature-R",
        writepv="SIM:TEMP:Temperature-S",
        use_prec=False,
    ),
)
```

The moveable classes require `readpv` and `writepv`. Configure `targetpv` when
the IOC provides a separate target readback. Without `targetpv`, updates from
`writepv` update the NICOS target.

The mapped classes read their mapping from IOC enum choices. Set
`_mapping_channel = "write"` in a subclass when the write PV defines the
choices.

## Write a device class

Add a class when several PVs form one NICOS device or when the device has
status or command rules.

The class needs:

- `EpicsDeviceBase` and a NICOS behavior class such as `Readable` or
  `Moveable`.
- A parameter containing the PV root.
- `_default_pv_prefix_attr` naming that parameter.
- `_primary_channel` naming the main readback.
- `_epics_channels` containing the PV suffixes.
- The methods required by the NICOS behavior class, such as `doStart()` for a
  `Moveable`.

`EpicsDeviceBase` handles wrapper creation, connections, subscriptions, cache
updates, units, EPICS alarms, connection status, and shutdown.

Three hooks cover most subclass needs: `_build_epics_channels()` when the
channel table depends on parameters, `_compute_status()` for device status
rules, and `_after_subscribe()` for setup that must wait until monitors are
wired. Each is shown below.

## Channel declarations

Use these constructors in `_epics_channels`:

- `readback_channel()` for a value read from EPICS.
- `setpoint_channel()` for a writable value that is also monitored.
- `status_channel()` for a value used by `_compute_status()`. Its updates
  recompute status and its connection state affects status.
- `command_channel()` for a write action such as reset or stop.
- The `enum_*_channel()` variants for NTEnum PVs.

`primary=True` marks the main value and alarm source. Use `cache_key="value"`
for the main readback and `cache_key="target"` for the setpoint. An omitted
cache key stores the value under the logical channel name.

Set `refresh_status=True` on a readback or setpoint when its updates can change
`_compute_status()`. `status_channel()` enables this by default.

Updates for all channels in one component are delivered to the device
serially. This keeps one channel's cache-and-status refresh from interleaving
with another channel's refresh. It does not make values published as separate
PVs an atomic IOC snapshot: when status requires a combination that must never
be mixed across transitions, expose an authoritative aggregate PV or an IOC
sequence/version that lets the client identify a coherent snapshot.

The default PV resolution is:

```text
<value of _default_pv_prefix_attr><channel suffix>
```

No separator is added. A root of `SIM:TEMP:` and a suffix of `Temperature-R`
resolve to `SIM:TEMP:Temperature-R`.

Use `pv_name_attr` when a parameter contains the complete PV name. Set the
channel suffix to `""`; the component then uses the parameter value instead of
joining a root and suffix.

Use `_build_epics_channels()` when a parameter controls whether the channel is
present. This example adds a reset command only when `reset_pv` is configured:

```python
from nicos.core import Param, none_or, pvname

from nicos_ess.devices.epics.pva.epics_common import command_channel


parameters = {
    "reset_pv": Param(
        "Reset PV",
        type=none_or(pvname),
        default=None,
        mandatory=False,
    ),
}


def _build_epics_channels(self):
    channels = dict(super()._build_epics_channels())
    if self.reset_pv:
        channels["reset"] = command_channel(
            "",
            pv_name_attr="reset_pv",
        )
    return channels
```

For an always-present full PV, declare the channel directly in
`_epics_channels` with `pv_suffix=""` and `pv_name_attr`.

Use `_after_subscribe(mode)` for setup that must wait until the channels are
connected and, in the poller, monitors are wired. The mapped classes use it to
read their mapping from the IOC enum choices:

```python
def _after_subscribe(self, mode):
    if mode != SIMULATION:
        self._update_mapped_choices()
    MappedReadable.doInit(self, mode)
```

## Temperature controller example

This controller has a temperature readback, temperature setpoint, On/Off loop
control, status message, and error bit.

```python
from nicos.core import (
    HasPrecision,
    Moveable,
    MoveError,
    Override,
    Param,
    pvname,
    status,
)

from nicos_ess.devices.epics.pva.epics_common import (
    EpicsDeviceBase,
    EpicsEnumParam,
    enum_setpoint_channel,
    readback_channel,
    setpoint_channel,
    status_channel,
    worst_status,
)


class EpicsTemperatureController(EpicsDeviceBase, HasPrecision, Moveable):
    parameters = {
        "pv_root": Param(
            "Temperature controller PV root",
            type=pvname,
            mandatory=True,
            userparam=False,
        ),
        "loop_control": Param(
            "Temperature loop state",
            type=EpicsEnumParam("loop"),
            mandatory=False,
            settable=True,
            volatile=True,
        ),
    }

    parameter_overrides = {
        "unit": Override(mandatory=False, settable=False, volatile=True),
    }

    valuetype = float
    errorstates = {**Moveable.errorstates, status.UNKNOWN: MoveError}

    _default_pv_prefix_attr = "pv_root"
    _primary_channel = "readback"
    _epics_channels = {
        "readback": readback_channel(
            "Temperature-R",
            cache_key="value",
            primary=True,
        ),
        "setpoint": setpoint_channel(
            "Temperature-S",
            refresh_status=True,
        ),
        "loop": enum_setpoint_channel(
            "Loop-S",
            cache_key="loop_control",
            refresh_status=True,
        ),
        "message": status_channel("Message-R", as_string=True),
        "error": status_channel("Error-R"),
    }

    def doReadTarget(self):
        return self._read_channel_cached("setpoint")

    def doStart(self, target):
        self._epics.put_channel_value("setpoint", target)

    def doReadLoop_Control(self):
        return self._epics.get_channel_value("loop")

    def doWriteLoop_Control(self, value):
        self._epics.put_channel_value("loop", value)
        return value

    def _compute_status(self, maxage=0):
        message = self._read_channel_cached("message", maxage=maxage)
        if self._read_channel_cached("error", maxage=maxage):
            device_status = status.ERROR, message
        elif self._read_channel_cached("loop", maxage=maxage) == "On" and not (
            self.isAtTarget(
                self._read_channel_cached("readback", maxage=maxage),
                self._read_channel_cached("setpoint", maxage=maxage),
            )
        ):
            device_status = status.BUSY, message
        else:
            device_status = status.OK, message
        return worst_status(device_status, self._read_primary_alarm(maxage=maxage))
```

`doRead()` comes from `EpicsDeviceBase` and reads the `readback` channel.
`HasPrecision` supplies the target comparison. Configure `precision` in the
setup.

`EpicsEnumParam("loop")` reads the On/Off choices from the `loop` channel.
The GUI uses those choices for `loop_control`. Assigning
`controller.loop_control = "On"` calls `doWriteLoop_Control()`.

Write channel values through `put_channel_value()`.

Two read paths exist and the choice matters:

- `_read_channel_cached(channel, maxage=...)` returns the monitor-fed cache
  value and falls back to a blocking IOC read. Use it in `doRead()` and
  `_compute_status()`, which receive `maxage` and run often.
- `self._epics.get_channel_value(channel)` always asks the IOC. Use it in
  `doRead<Param>()` for `volatile=True` parameters: volatile means the value
  must come from hardware, and a cached read just after a write can return
  the old value. The daemon calls these on every parameter access, so this
  is a blocking network read on the caller's thread.

`target` is the exception, as in `doReadTarget()` above. It is not a volatile
parameter: monitors write the `target` cache key, which is how external
setpoint writes become the NICOS target, and the non-volatile getter serves
`device.target` from that cache. `doReadTarget()` only runs in poller
parameter sweeps and when monitoring is off.

Override `_compute_status()` for device status rules. Return a NICOS
`(severity, message)` tuple. Keep `doStatus()` on the base class so connection
status is included.

Override `_on_channel_update()` when a monitor value needs conversion before
it enters the cache. Call `super()._on_channel_update(update)` after the
conversion.

## Test device-specific behavior

The shared EPICS tests cover monitoring, PVA and CA wrappers, cache behavior,
and connection handling. A device test should cover its channel wiring and
custom NICOS logic.

Use `device_harness.create_pair()` so monitor updates run through a poller
device and are read by a daemon device.

```python
import pytest

from nicos.core import status
from nicos_ess.devices.epics.pva import epics_common
from nicos_ess.devices.epics.temperature_controller import (
    EpicsTemperatureController,
)


@pytest.fixture
def fake_backend(fake_epics_backend_factory):
    # EPICS network access is replaced so tests can drive IOC updates.
    return fake_epics_backend_factory(epics_common)


def create_controller_pair(device_harness, fake_backend):
    root = "SIM:TEMP:"
    values = {
        f"{root}Temperature-R": 295.0,
        f"{root}Temperature-S": 295.0,
        f"{root}Loop-S": 0,
        f"{root}Message-R": "loop off",
        f"{root}Error-R": 0,
    }
    fake_backend.values.update(values)
    fake_backend.value_choices[f"{root}Loop-S"] = ["Off", "On"]
    fake_backend.alarms[f"{root}Temperature-R"] = (status.OK, "")

    devices = device_harness.create_pair(
        EpicsTemperatureController,
        name="temperature_controller",
        shared={"pv_root": root, "precision": 0.1},
    )
    return root, devices


def test_loop_control_uses_ioc_choices(device_harness, fake_backend):
    root, (controller, _poller) = create_controller_pair(
        device_harness, fake_backend
    )

    assert controller.parameters["loop_control"].type.vals == ("Off", "On")
    device_harness.run("daemon", setattr, controller, "loop_control", "On")

    assert fake_backend.put_calls[-1] == (f"{root}Loop-S", "On", False)


def test_status_uses_temperature_message_and_error(
    device_harness, fake_backend
):
    root, (controller, _poller) = create_controller_pair(
        device_harness, fake_backend
    )

    fake_backend.emit_update(f"{root}Temperature-S", value=300.0)
    fake_backend.emit_update(f"{root}Loop-S", value=1)
    fake_backend.emit_update(f"{root}Message-R", value="heating")
    fake_backend.emit_update(f"{root}Temperature-R", value=298.0)

    assert device_harness.run("daemon", controller.status) == (
        status.BUSY,
        "heating",
    )

    fake_backend.emit_update(f"{root}Message-R", value="sensor fault")
    fake_backend.emit_update(f"{root}Error-R", value=1)

    assert device_harness.run("daemon", controller.status) == (
        status.ERROR,
        "sensor fault",
    )
```

Run the device test:

```text
uv run pytest test/nicos_ess/test_devices/test_temperature_controller.py -q
```

## Read from two IOCs

Use a separate root parameter and `pv_prefix_attr` for channels served by
another IOC.

```python
from nicos.core import Override, Param, Readable, pvname, status

from nicos_ess.devices.epics.pva.epics_common import (
    EpicsDeviceBase,
    readback_channel,
    status_channel,
    worst_status,
)


class VacuumPressure(EpicsDeviceBase, Readable):
    parameters = {
        "pressure_pv_root": Param(
            "Pressure IOC PV root", type=pvname, mandatory=True
        ),
        "status_pv_root": Param(
            "Status IOC PV root", type=pvname, mandatory=True
        ),
    }

    parameter_overrides = {
        "unit": Override(mandatory=False, settable=False, volatile=True),
    }

    _default_pv_prefix_attr = "pressure_pv_root"
    _primary_channel = "pressure"
    _epics_channels = {
        "pressure": readback_channel(
            "Pressure-R", cache_key="value", primary=True
        ),
        "vacuum_status": status_channel(
            "Status-R",
            as_string=True,
            pv_prefix_attr="status_pv_root",
        ),
    }

    def _compute_status(self, maxage=0):
        value = self._read_channel_cached("vacuum_status", maxage=maxage)
        code = {
            "OK": status.OK,
            "Warning": status.WARN,
            "Error": status.ERROR,
        }.get(value, status.UNKNOWN)
        return worst_status(
            (code, value), self._read_primary_alarm(maxage=maxage)
        )
```

With `pressure_pv_root="SIM:VAC:"` and
`status_pv_root="SIM:VAC-CTRL:"`, the channels resolve to
`SIM:VAC:Pressure-R` and `SIM:VAC-CTRL:Status-R`. Startup checks both IOCs, and
loss of either channel affects device status.
