# *****************************************************************************
# NICOS, the Networked Instrument Control System of the MLZ
# Copyright (c) 2009-2024 by the NICOS contributors (see AUTHORS)
#
# This program is free software; you can redistribute it and/or modify it under
# the terms of the GNU General Public License as published by the Free Software
# Foundation; either version 2 of the License, or (at your option) any later
# version.
#
# This program is distributed in the hope that it will be useful, but WITHOUT
# ANY WARRANTY; without even the implied warranty of MERCHANTABILITY or FITNESS
# FOR A PARTICULAR PURPOSE.  See the GNU General Public License for more
# details.
#
# You should have received a copy of the GNU General Public License along with
# this program; if not, write to the Free Software Foundation, Inc.,
# 59 Temple Place, Suite 330, Boston, MA  02111-1307  USA
#
# Module authors:
#
#   Jonas Petersson <jonas.petersson@ess.eu>
#
# *****************************************************************************

import pytest

from nicos.core import MoveError, PositionError, status
from nicos_ess.devices.epics.pva import epics_common, shutter
from test.nicos_ess.test_devices.doubles import FakeEpicsBackend


@pytest.fixture
def fake_backend(monkeypatch):
    class ShutterBackend(FakeEpicsBackend):
        def __init__(self):
            super().__init__()
            self._ack_due = False

        def put_pv_value(self, pvname, value, wait=False):
            super().put_pv_value(pvname, value, wait)
            if pvname == "SIM:SHUTTER:WRITE":
                self._ack_due = True

        def get_pv_value(self, pvname, as_string=False):
            value = super().get_pv_value(pvname, as_string)
            if pvname == "SIM:SHUTTER:STATUS" and self._ack_due:
                # Model the IOC callback arriving just after a direct read
                # still returned the previous command's IDLE.
                self._ack_due = False
                self.emit_update(pvname, value="START")
            return value

    backend = ShutterBackend()
    # Network boundary: replace the PVA wrapper factory with the in-memory backend.
    monkeypatch.setattr(
        epics_common, "create_wrapper", lambda timeout, use_pva: backend
    )
    backend.values["SIM:SHUTTER:READ"] = "Closed"
    backend.values["SIM:SHUTTER:WRITE"] = "Close"
    backend.values["SIM:SHUTTER:MSGTXT"] = ""
    backend.values["SIM:SHUTTER:STATUS"] = "IDLE"
    backend.value_choices["SIM:SHUTTER:READ"] = [
        "Closed",
        "Closing",
        "Opening",
        "Opened",
        "InBeam",
    ]
    backend.value_choices["SIM:SHUTTER:WRITE"] = [
        "Close",
        "Open",
    ]
    backend.value_choices["SIM:SHUTTER:STATUS"] = [
        "RESET",
        "IDLE",
        "DISABLED",
        "WARN",
        "ERR-4",
        "START",
        "BUSY",
        "STOP",
        "ERROR",
    ]
    return backend


@pytest.fixture
def shutter_device(device_harness, fake_backend):
    del fake_backend
    return device_harness.create(
        "daemon",
        shutter.EpicsShutter,
        name="epics_shutter",
        readpv="SIM:SHUTTER:READ",
        writepv="SIM:SHUTTER:WRITE",
        statuspv="SIM:SHUTTER:STATUS",
        msgtxt="SIM:SHUTTER:MSGTXT",
        monitor=False,
    )


class TestEpicsShutterHarness:
    def test_numeric_state_uses_readback_choices(self, device_harness, shutter_device):
        result = device_harness.run("daemon", shutter_device._normalize_readback, 3)

        assert result == "Opened"

    @pytest.mark.parametrize("value", [99, 1.5])
    def test_invalid_numeric_state_is_rejected(
        self, device_harness, shutter_device, value
    ):
        with pytest.raises(PositionError, match="unknown unmapped position"):
            device_harness.run("daemon", shutter_device._normalize_readback, value)

    def test_initializes(self, device_harness, fake_backend):
        del fake_backend
        assert shutter.EpicsShutter.parameters["msgtxt"].mandatory
        assert shutter.EpicsShutter.parameters["statuspv"].mandatory
        daemon_device, poller_device = device_harness.create_pair(
            shutter.EpicsShutter,
            name="epics_shutter",
            shared={
                "readpv": "SIM:SHUTTER:READ",
                "writepv": "SIM:SHUTTER:WRITE",
                "statuspv": "SIM:SHUTTER:STATUS",
                "msgtxt": "SIM:SHUTTER:MSGTXT",
                "mapping": {"Close": "Close", "Open": "Open"},
                "monitor": True,
                "pva": True,
            },
        )

        assert daemon_device is not None
        assert poller_device is not None

    def test_publishes_write_choices_but_accepts_readback_states(
        self, device_harness, fake_backend
    ):
        daemon_device, poller_device = device_harness.create_pair(
            shutter.EpicsShutter,
            name="epics_shutter",
            shared={
                "readpv": "SIM:SHUTTER:READ",
                "writepv": "SIM:SHUTTER:WRITE",
                "statuspv": "SIM:SHUTTER:STATUS",
                "msgtxt": "SIM:SHUTTER:MSGTXT",
                "mapping": {"Close": 0, "Open": 1},
                "monitor": True,
                "pva": True,
            },
        )

        assert device_harness.run("daemon", lambda: daemon_device.mapping) == {
            "Close": 0,
            "Open": 1,
        }
        assert device_harness.run("poller", lambda: poller_device.mapping) == {
            "Close": 0,
            "Open": 1,
        }

        fake_backend.emit_update("SIM:SHUTTER:READ", value="Opening", units="")
        fake_backend.emit_update("SIM:SHUTTER:STATUS", value="BUSY")

        assert device_harness.run("daemon", daemon_device.read) == "Opening"
        assert device_harness.run("daemon", daemon_device.status) == (
            status.BUSY,
            "moving",
        )

        device_harness.run("daemon", daemon_device.start, "Open")

        assert fake_backend.put_calls[-1] == ("SIM:SHUTTER:WRITE", 1, False)

    def test_fresh_status_bypasses_a_stale_cached_message(
        self, device_harness, fake_backend
    ):
        daemon_device, _poller_device = device_harness.create_pair(
            shutter.EpicsShutter,
            name="epics_shutter",
            shared={
                "readpv": "SIM:SHUTTER:READ",
                "writepv": "SIM:SHUTTER:WRITE",
                "statuspv": "SIM:SHUTTER:STATUS",
                "msgtxt": "SIM:SHUTTER:MSGTXT",
                "mapping": {"Close": 0, "Open": 1},
                "monitor": True,
                "pva": True,
            },
        )

        fake_backend.emit_update("SIM:SHUTTER:MSGTXT", value="Opening")
        fake_backend.emit_update("SIM:SHUTTER:READ", value="Opening")
        fake_backend.emit_update("SIM:SHUTTER:STATUS", value="BUSY")
        assert device_harness.run("daemon", daemon_device.status) == (
            status.BUSY,
            "Opening",
        )

        # The IOC has completed, but its terminal monitor events have not yet
        # propagated from the poller to this daemon-side device instance.
        fake_backend.values["SIM:SHUTTER:READ"] = "Opened"
        fake_backend.values["SIM:SHUTTER:MSGTXT"] = "Open"
        fake_backend.values["SIM:SHUTTER:STATUS"] = "IDLE"

        assert device_harness.run("daemon", daemon_device.status, 0) == (
            status.OK,
            "Open",
        )

    def test_fresh_status_reports_unknown_when_auxiliary_pvs_time_out(
        self, device_harness, fake_backend
    ):
        daemon_device, _poller_device = device_harness.create_pair(
            shutter.EpicsShutter,
            name="epics_shutter",
            shared={
                "readpv": "SIM:SHUTTER:READ",
                "writepv": "SIM:SHUTTER:WRITE",
                "statuspv": "SIM:SHUTTER:STATUS",
                "msgtxt": "SIM:SHUTTER:MSGTXT",
                "monitor": True,
                "pva": True,
            },
        )
        fake_backend.disconnect_backend()

        assert device_harness.run("daemon", daemon_device.status, 0) == (
            status.UNKNOWN,
            "lost connection to EPICS",
        )

    def test_start_waits_for_status_code_acknowledgement_before_returning(
        self, device_harness, fake_backend
    ):
        daemon_device, _poller_device = device_harness.create_pair(
            shutter.EpicsShutter,
            name="epics_shutter",
            shared={
                "readpv": "SIM:SHUTTER:READ",
                "writepv": "SIM:SHUTTER:WRITE",
                "statuspv": "SIM:SHUTTER:STATUS",
                "msgtxt": "SIM:SHUTTER:MSGTXT",
                "monitor": True,
                "pva": True,
            },
        )

        device_harness.run("daemon", daemon_device.start, "Open")

        # The command PV write returned while the first status read still saw
        # the previous IDLE.  The temporary monitor delivered START, so start
        # only returns once status(0) can no longer complete against old data.
        assert fake_backend.values["SIM:SHUTTER:READ"] == "Closed"
        assert fake_backend.values["SIM:SHUTTER:STATUS"] == "START"
        assert device_harness.run("daemon", lambda: daemon_device.target) == "Open"
        assert device_harness.run("daemon", daemon_device.status, 0) == (
            status.BUSY,
            "moving to Open",
        )
        assert device_harness.run("daemon", daemon_device.isCompleted) is False

        fake_backend.emit_update("SIM:SHUTTER:STATUS", value="BUSY")
        fake_backend.emit_update("SIM:SHUTTER:READ", value="InBeam")
        fake_backend.emit_update("SIM:SHUTTER:MSGTXT", value="In beam")
        assert device_harness.run("daemon", daemon_device.isCompleted) is False

        fake_backend.emit_update("SIM:SHUTTER:STATUS", value="IDLE")

        assert device_harness.run("daemon", daemon_device.read) == "InBeam"
        assert device_harness.run("daemon", daemon_device.status, 0) == (
            status.OK,
            "In beam",
        )
        assert device_harness.run("daemon", daemon_device.isCompleted) is True

    def test_status_code_completion_works_without_monitors_or_pollinterval(
        self, device_harness, fake_backend
    ):
        daemon_device = device_harness.create(
            "daemon",
            shutter.EpicsShutter,
            name="epics_shutter",
            readpv="SIM:SHUTTER:READ",
            writepv="SIM:SHUTTER:WRITE",
            statuspv="SIM:SHUTTER:STATUS",
            msgtxt="SIM:SHUTTER:MSGTXT",
            monitor=False,
            pollinterval=None,
            pva=True,
        )

        device_harness.run("daemon", daemon_device.start, "Open")
        assert device_harness.run("daemon", daemon_device.isCompleted) is False

        fake_backend.values["SIM:SHUTTER:STATUS"] = "START"
        assert device_harness.run("daemon", daemon_device.isCompleted) is False

        fake_backend.values["SIM:SHUTTER:STATUS"] = "BUSY"
        assert device_harness.run("daemon", daemon_device.isCompleted) is False

        fake_backend.values["SIM:SHUTTER:READ"] = "InBeam"
        fake_backend.values["SIM:SHUTTER:MSGTXT"] = "In beam"
        fake_backend.values["SIM:SHUTTER:STATUS"] = "IDLE"
        assert device_harness.run("daemon", daemon_device.isCompleted) is True

    def test_status_code_error_fails_an_active_move(self, device_harness, fake_backend):
        daemon_device, _poller_device = device_harness.create_pair(
            shutter.EpicsShutter,
            name="epics_shutter",
            shared={
                "readpv": "SIM:SHUTTER:READ",
                "writepv": "SIM:SHUTTER:WRITE",
                "statuspv": "SIM:SHUTTER:STATUS",
                "msgtxt": "SIM:SHUTTER:MSGTXT",
                "monitor": True,
                "pva": True,
            },
        )

        device_harness.run("daemon", daemon_device.start, "Open")
        fake_backend.emit_update("SIM:SHUTTER:MSGTXT", value="E: Air pressure low")
        fake_backend.emit_update("SIM:SHUTTER:STATUS", value="ERROR")

        with pytest.raises(MoveError, match="Air pressure low"):
            device_harness.run("daemon", daemon_device.isCompleted)
