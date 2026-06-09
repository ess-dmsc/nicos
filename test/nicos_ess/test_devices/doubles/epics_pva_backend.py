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

"""EPICS backend doubles for PVA device tests."""

from functools import wraps

from nicos.core import status


def _requires_connected_backend(func):
    """Raise an EPICS-style timeout while the fake backend is disconnected."""

    @wraps(func)
    def wrapper(self, pvname, *args, **kwargs):
        if not self._is_connected:
            raise TimeoutError(f"{pvname} timed out") from None
        return func(self, pvname, *args, **kwargs)

    return wrapper


class FakeEpicsBackend:
    """In-memory EPICS backend for device tests."""

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
        self._is_connected = True

    def connect_pv(self, pvname):
        self.connect_calls.append(pvname)

    def _get_value(self, pvname, as_string=False):
        value = self.values[pvname]
        if not as_string:
            return value

        choices = self.value_choices.get(pvname)
        if choices and isinstance(value, int):
            try:
                return choices[value]
            except IndexError:
                return value
        if isinstance(value, bytes):
            return value.decode()
        if hasattr(value, "tolist"):
            value = value.tolist()
        if isinstance(value, (list, tuple)):
            return "".join(chr(int(x)) for x in value)
        return str(value)

    @_requires_connected_backend
    def get_pv_value(self, pvname, as_string=False):
        self.get_calls.append(("get_pv_value", pvname, as_string))
        return self._get_value(pvname, as_string)

    @_requires_connected_backend
    def get_units(self, pvname, default=""):
        self.get_calls.append(("get_units", pvname, default))
        return self.units.get(pvname, default)

    @_requires_connected_backend
    def get_alarm_status(self, pvname):
        self.get_calls.append(("get_alarm_status", pvname, None))
        return self.alarms.get(pvname, (status.OK, ""))

    @_requires_connected_backend
    def get_limits(self, pvname, default_low=-1e308, default_high=1e308):
        self.get_calls.append(("get_limits", pvname, (default_low, default_high)))
        return self.limits.get(pvname, (default_low, default_high))

    @_requires_connected_backend
    def get_value_choices(self, pvname):
        self.get_calls.append(("get_value_choices", pvname, None))
        return list(self.value_choices.get(pvname, ()))

    @_requires_connected_backend
    def put_pv_value(self, pvname, value, wait=False):
        self.values[pvname] = value
        self.put_calls.append((pvname, value, wait))

    def disconnect_backend(self):
        self._is_connected = False
        self._emit_all_connections(False)

    def connect_backend(self):
        self._is_connected = True
        self._emit_all_connections(True)

    def _emit_all_connections(self, is_connected):
        for sub_pv, pvparam, _, connection_callback, _ in list(self.subscriptions):
            if connection_callback:
                connection_callback(sub_pv, pvparam, is_connected)

    def subscribe(
        self,
        pvname,
        pvparam,
        change_callback,
        connection_callback=None,
        as_string=False,
    ):
        token = (pvname, pvparam, change_callback, connection_callback, as_string)
        self.subscriptions.append(token)
        return token

    def close_subscription(self, subscription):
        if subscription in self.subscriptions:
            self.subscriptions.remove(subscription)

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
        for sub_pv, pvparam, change_callback, _, as_string in list(self.subscriptions):
            if sub_pv == pv:
                change_callback(
                    pv,
                    pvparam,
                    self._get_value(pv, as_string),
                    units,
                    limits,
                    severity,
                    message,
                )

    def emit_connection(self, pv, is_connected):
        for sub_pv, pvparam, _, connection_callback, _ in list(self.subscriptions):
            if sub_pv == pv and connection_callback:
                connection_callback(pv, pvparam, is_connected)


def patch_create_wrapper(monkeypatch, module):
    """Patch ``create_wrapper`` to return a shared fake backend."""
    backend = FakeEpicsBackend()

    def make_backend(timeout, use_pva):
        del timeout, use_pva
        return backend

    from nicos_ess.devices.epics.pva import epics_common

    monkeypatch.setattr(epics_common, "create_wrapper", make_backend, raising=False)
    monkeypatch.setattr(
        module, "create_wrapper", make_backend, raising=False
    )
    return backend


def analog_moveable_config():
    return {
        "readpv": "SIM:M1.RBV",
        "writepv": "SIM:M1.VAL",
        "unit": "mm",
        "abslimits": (-120.0, 120.0),
    }


def string_moveable_config():
    return {
        "readpv": "SIM:SEL.RBV",
        "writepv": "SIM:SEL.VAL",
        "unit": "",
    }


def mapped_config():
    return {
        "readpv": "SIM:MAP.RBV",
        "writepv": "SIM:MAP.VAL",
        "mapping": {"OFF": 0, "ON": 1},
        "unit": "",
    }
