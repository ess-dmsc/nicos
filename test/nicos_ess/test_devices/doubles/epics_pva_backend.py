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

"""Reusable EPICS backend doubles for pva `epics_devices` harness tests."""

from nicos.core import status


class FakeEpicsBackend:
    """In-memory EPICS backend used by unit tests.

    The class intentionally mirrors the tiny API consumed by
    `nicos_ess.devices.epics.pva.epics_devices`.
    """

    def __init__(self):
        self.values = {}
        self.units = {}
        self.limits = {}
        self.alarms = {}
        self.value_choices = {}
        self.connect_calls = []
        self.put_calls = []
        self.get_calls = []
        self.subscriptions = []

    def connect_pv(self, pvname):
        self.connect_calls.append(pvname)

    def get_pv_value(self, pvname, as_string=False):
        self.get_calls.append(("get_pv_value", pvname, as_string))
        return self.values[pvname]

    def get_units(self, pvname, default=""):
        self.get_calls.append(("get_units", pvname, default))
        return self.units.get(pvname, default)

    def get_alarm_status(self, pvname):
        self.get_calls.append(("get_alarm_status", pvname, None))
        return self.alarms.get(pvname, (status.OK, ""))

    def get_limits(self, pvname, default_low=-1e308, default_high=1e308):
        self.get_calls.append(("get_limits", pvname, (default_low, default_high)))
        return self.limits.get(pvname, (default_low, default_high))

    def get_value_choices(self, pvname):
        self.get_calls.append(("get_value_choices", pvname, None))
        return list(self.value_choices.get(pvname, ()))

    def put_pv_value(self, pvname, value, wait=False):
        self.values[pvname] = value
        self.put_calls.append((pvname, value, wait))

    def subscribe(
        self,
        pvname,
        pvparam,
        change_callback,
        connection_callback=None,
        as_string=False,
    ):
        del as_string
        token = (pvname, pvparam, change_callback, connection_callback)
        self.subscriptions.append(token)
        return token

    def emit_update(
        self,
        pv,
        *,
        value=None,
        units="",
        limits=None,
        severity=status.OK,
        message="",
    ):
        if value is not None:
            self.values[pv] = value
        current_value = self.values[pv]
        for sub_pv, pvparam, change_callback, _ in list(self.subscriptions):
            if sub_pv == pv:
                change_callback(
                    pv,
                    pvparam,
                    current_value,
                    units,
                    limits,
                    severity,
                    message,
                )

    def emit_connection(self, pv, is_connected):
        for sub_pv, pvparam, _, connection_callback in list(self.subscriptions):
            if sub_pv == pv:
                if connection_callback:
                    connection_callback(pv, pvparam, is_connected)


def patch_create_wrapper(monkeypatch, epics_devices_module):
    """Patch `create_wrapper` in `epics_devices` and return backend + factory."""
    backend = FakeEpicsBackend()
    monkeypatch.setattr(
        epics_devices_module,
        "create_wrapper",
        lambda timeout, use_pva: backend,
    )
    return backend


def analog_moveable_config():
    """Configuration that mirrors common ESS setup usage."""
    return {
        "readpv": "SIM:M1.RBV",
        "writepv": "SIM:M1.VAL",
        "unit": "mm",
        "abslimits": (-120.0, 120.0),
    }


def string_moveable_config():
    """Setup-style config for string moveables."""
    return {
        "readpv": "SIM:SEL.RBV",
        "writepv": "SIM:SEL.VAL",
        "unit": "",
    }


def mapped_config():
    """Common mapped configuration used by mapped readable/moveable classes."""
    return {
        "readpv": "SIM:MAP.RBV",
        "writepv": "SIM:MAP.VAL",
        "mapping": {"OFF": 0, "ON": 1},
        "unit": "",
    }
