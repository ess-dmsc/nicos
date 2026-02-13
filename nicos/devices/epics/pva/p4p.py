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
#   Matt Clarke <matt.clarke@ess.eu>
#
# *****************************************************************************
from collections import defaultdict
from collections.abc import Iterable
from functools import partial
from threading import Lock

import numpy as np
from p4p.client.thread import Cancelled, Context

from nicos.commands import helparglist, hiddenusercommand
from nicos.core import CommunicationError, status
from nicos.devices.epics.status import SEVERITY_TO_STATUS

# Same context can be shared across all devices.
# nt=False tells p4p not to try to map types itself
# we want to do this manually to avoid information loss
_CONTEXT = Context("pva", nt=False)


@hiddenusercommand
@helparglist("name[, timeout]")
def pvget(name, timeout=3.0):
    """Returns the PV's current value in its raw form via PVA.

    :param name: the PV name
    :param timeout: the EPICS timeout
    :return: the PV's raw value
    """
    response = _CONTEXT.get(name, timeout=timeout)
    return response["value"]


@hiddenusercommand
@helparglist("name, value[, wait, timeout]")
def pvput(name, value, wait=False, timeout=3.0):
    """Sets a PV's value via PVA.

    :param name: the PV name
    :param value: the value to set
    :param wait: whether to wait for completion
    :param timeout: the EPICS timeout
    """
    _CONTEXT.put(name, value, timeout=timeout, wait=wait, process="true")


class P4pWrapper:
    """Class that wraps the p4p module that provides EPICS PVA Access (PVA)
    support.
    """

    def __init__(self, timeout=3.0, context=None):
        # We can have multiple monitors per PV (value/status/etc). p4p can inject
        # an initial Disconnected and deliver connect/disconnect out-of-order.
        # Track per-sub connected state + per-(pv,param) refcount.
        self._sub_connected = {}
        self._conn_refcnt = defaultdict(int)
        self._sub_to_key = {}

        self._context = context or _CONTEXT

        self.lock = Lock()
        self._timeout = timeout
        self._units = {}
        self._values = {}
        self._alarms = {}
        self._choices = {}
        self._limits = {}

    def connect_pv(self, pvname):
        # Check pv is available
        try:
            self._context.get(pvname, timeout=self._timeout)
        except TimeoutError:
            raise CommunicationError(f"could not connect to PV {pvname}") from None

    def get_pv_value(self, pvname, as_string=False):
        result = self._context.get(pvname, timeout=self._timeout)
        return self._convert_value(pvname, result["value"], as_string)

    def _convert_value(self, pvname, value, as_string=False):
        try:
            # Enums are complicated
            if value.getID() == "enum_t":
                index = value["index"]
                if as_string:
                    if pvname not in self._choices:
                        self.get_value_choices(pvname)
                    return self._choices[pvname][index]
                return index
        except AttributeError:
            # getID() doesn't (currently) exist for scalar
            # and scalar-array types
            pass

        if as_string:
            # waveforms and arrays are already ndarrays
            if isinstance(value, np.ndarray):
                return value.tostring().decode()
            else:
                return str(value)
        return value

    def put_pv_value(self, pvname, value, wait=False):
        self._context.put(
            pvname, value, timeout=self._timeout, wait=wait, process="true"
        )

    def put_pv_value_blocking(self, pvname, value, block_timeout=60):
        self._context.put(
            pvname, value, timeout=block_timeout, wait=True, process="true"
        )

    def get_pv_type(self, pvname):
        result = self._context.get(pvname, timeout=self._timeout)
        try:
            if result["value"].getID() == "enum_t":
                # Treat enums as ints
                return int
        except AttributeError:
            # getID() doesn't (currently) exist for scalar
            # and scalar-array types
            pass

        return type(result["value"])

    def get_alarm_status(self, pvname):
        result = self._context.get(pvname, timeout=self._timeout)
        return self._extract_alarm_info(result)

    def get_units(self, pvname, default=""):
        result = self._context.get(pvname, timeout=self._timeout)
        return self._get_units(result, default)

    def _get_units(self, result, default):
        try:
            return result["display"]["units"]
        except KeyError:
            return default

    def get_limits(self, pvname, default_low=-1e308, default_high=1e308):
        result = self._context.get(pvname, timeout=self._timeout)
        return self._extract_limits(result, default_low, default_high)

    def _extract_limits(self, result, default_low=-1e308, default_high=1e308):
        try:
            default_low = result["display"]["limitLow"]
            default_high = result["display"]["limitHigh"]
        except KeyError:
            pass
        return default_low, default_high

    def get_control_values(self, pvname):
        raw_result = self._context.get(pvname, timeout=self._timeout)
        if "display" in raw_result:
            return raw_result["display"]
        return raw_result["control"] if "control" in raw_result else {}

    def get_value_choices(self, pvname):
        value = self._context.get(pvname, timeout=self._timeout)["value"]
        if isinstance(value, bool):
            return [False, True]
        if not isinstance(value, Iterable):
            return []
        if "choices" in value:
            self._choices[pvname] = value["choices"]
            return self._choices[pvname]
        return []

    def subscribe(
        self,
        pvname,
        pvparam,
        change_callback,
        connection_callback=None,
        as_string=False,
    ):
        """
        Create a monitor subscription to the specified PV.

        Callback signatures:

          change_callback(
              pvname,
              pvparam,
              value,
              units,
              limits,
              severity,
              message,
              **kwargs,
          )

          connection_callback(
              pvname,
              pvparam,
              is_connected,
              **kwargs,
          )

        Notes:
          - On disconnect, connection_callback may receive reason=<str> in kwargs.
        """
        request = "field(value,timeStamp,alarm,control,display)"

        token = object()
        subkey = (pvname, pvparam, token)

        with self.lock:
            self._sub_connected[subkey] = False

        callback = partial(
            self._callback,
            subkey,
            change_callback,
            connection_callback,
            as_string,
        )
        sub = self._context.monitor(
            pvname, callback, request=request, notify_disconnect=True
        )

        self._sub_to_key[id(sub)] = subkey

        return sub

    def _callback(
        self,
        subkey,
        change_callback,
        connection_callback,
        as_string,
        result,
    ):
        pvname, pvparam, _ = subkey
        conn_key = subkey[:2]

        if isinstance(result, Exception):
            with self.lock:
                was_connected = self._sub_connected.get(subkey, False)
                if was_connected:
                    self._sub_connected[subkey] = False
                    if self._conn_refcnt[conn_key] > 0:
                        self._conn_refcnt[conn_key] -= 1
                    last_sub_went_down = self._conn_refcnt[conn_key] == 0
                    if last_sub_went_down:
                        self._conn_refcnt.pop(conn_key, None)
                else:
                    last_sub_went_down = False

            # Cancelled is usually shutdown/reconfigure; not a comms failure.
            if isinstance(result, Cancelled):
                return

            if last_sub_went_down and connection_callback:
                connection_callback(pvname, pvparam, False, reason=repr(result))
            return

        with self.lock:
            first_sub_came_up = False
            if not self._sub_connected.get(subkey, False):
                self._sub_connected[subkey] = True
                self._conn_refcnt[conn_key] += 1
                first_sub_came_up = self._conn_refcnt[conn_key] == 1

        if first_sub_came_up and connection_callback:
            connection_callback(pvname, pvparam, True)

        if not change_callback:
            return

        # Monitor updates are deltas; alarm/status can change without "value".
        # Keep last value so we can still emit status updates.
        change_set = result.changedSet()

        with self.lock:
            if pvname not in self._values:
                try:
                    raw_value = result["value"]
                except KeyError:
                    raw_value = None
                if raw_value is not None:
                    self._values[pvname] = self._convert_value(
                        pvname,
                        raw_value,
                        as_string,
                    )

            if "value" in change_set or "value.index" in change_set:
                self._values[pvname] = self._convert_value(
                    pvname,
                    result["value"],
                    as_string,
                )

            if "value.index" in change_set:
                choices = result["value"].get("choices", [])
                if choices:
                    self._choices[pvname] = choices

            if "display.units" in change_set:
                self._units[pvname] = self._get_units(result, "")

            if "alarm.status" in change_set or "alarm.severity" in change_set:
                self._alarms[pvname] = self._extract_alarm_info(result)

            if "display.limitLow" in change_set:
                self._limits[pvname] = self._extract_limits(result)

            value = self._values.get(pvname)
            if value is None:
                return

            units = self._units.get(pvname, "")
            limits = self._limits.get(pvname, None)
            severity, msg = self._alarms.get(pvname, (status.UNKNOWN, ""))

        change_callback(
            pvname,
            pvparam,
            value,
            units,
            limits,
            severity,
            msg,
        )

    def _extract_alarm_info(self, value):
        # The EPICS 'severity' matches to the NICOS `status` and the message has
        # a short description of the alarm details.
        try:
            severity = SEVERITY_TO_STATUS[value["alarm"]["severity"]]
            message = value["alarm"]["message"]
            return severity, "" if message == "NO_ALARM" else message
        except KeyError:
            return status.UNKNOWN, "alarm information unavailable"

    def close_subscription(self, subscription):
        subkey = self._sub_to_key.pop(id(subscription), None)

        if subkey is not None:
            conn_key = subkey[:2]
            with self.lock:
                was_connected = self._sub_connected.pop(subkey, False)
                if was_connected and self._conn_refcnt[conn_key] > 0:
                    self._conn_refcnt[conn_key] -= 1
                if self._conn_refcnt.get(conn_key) == 0:
                    self._conn_refcnt.pop(conn_key, None)

        subscription.close()
