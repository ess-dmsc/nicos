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
#   Georg Brandl <g.brandl@fz-juelich.de>
#
# *****************************************************************************

"""NICOS-TACO base classes."""

import sys

import TACOStates  # pylint: disable=import-error
from TACOClient import TACOError  # pylint: disable=import-error

from nicos import session
from nicos.core import SIMULATION, CommunicationError, HasCommunication, \
    InvalidValueError, LimitError, NicosError, Override, Param, \
    ProgrammingError, floatrange, status, tacodev
from nicos.utils import HardwareStub

try:
    from TACOErrors import DevErr_ExecutionDenied, DevErr_InternalError, \
        DevErr_InvalidValue, DevErr_IOError, DevErr_RangeError, \
        DevErr_RuntimeError, DevErr_SystemError
except ImportError:
    DevErr_ExecutionDenied = 4010
    DevErr_RangeError      = 4017
    DevErr_InvalidValue    = 4018
    DevErr_RuntimeError    = 4019
    DevErr_InternalError   = 4020
    DevErr_IOError         = 4024
    DevErr_SystemError     = 4025

try:
    from DEVERRORS import DevErr_RPCTimedOut
except ImportError:
    DevErr_RPCTimedOut     = 2


class TacoDevice(HasCommunication):
    """Mixin class for TACO devices.

    Use it in concrete device classes like this::

        class Counter(TacoDevice, Measurable):
            taco_class = IO.Counter

            # more overwritten methods

    i.e., put TacoDevice first in the base class list.

    TacoDevice provides the following methods already:

    * `.doVersion` (returns TACO device version)
    * `.doPreinit` (creates the TACO device from the `tacodevice` parameter)
    * `.doRead` (reads the TACO device)
    * `.doStatus` (returns status.OK for ON and DEVICE_NORMAL, ERROR otherwise)
    * `.doReset` (resets the TACO device)
    * `.doReadUnit` (reads the unit parameter from the TACO device if not
      configured in setup)

    You can however override them and provide your own specialized
    implementation.

    TacoDevice subclasses will automatically log all calls to TACO if their
    loglevel is DEBUG.

    TacoDevice also has the following class attributes, which can be overridden
    in derived classes:

    * `taco_class` -- the Python class to use for the TACO client
    * `taco_resetok` -- a boolean value indicating if the device can be reset
      during connection if it is in error state
    * `taco_errorcodes` -- a dictionary mapping TACO error codes to NICOS
      exception classes

    The following utility methods are provided:

    .. automethod:: _taco_guard
    .. automethod:: _taco_update_resource
    .. automethod:: _create_client
    """

    parameters = {
        'tacodevice':  Param('TACO device name', type=tacodev, mandatory=True,
                             preinit=True),
        'tacotimeout': Param('TACO network timeout for this process',
                             unit='s', type=floatrange(0.0, 1200), default=3,
                             settable=True, preinit=True),
    }

    parameter_overrides = {
        # the unit isn't mandatory -- TACO usually knows it already
        'unit': Override(mandatory=False),
    }

    _TACO_STATUS_MAPPING = {
        # OK states
        TACOStates.ON: status.OK,
        TACOStates.DEVICE_NORMAL: (status.OK, 'idle'),
        TACOStates.POSITIVE_ENDSTOP: (status.OK, 'limit switch +'),
        TACOStates.NEGATIVE_ENDSTOP: (status.OK, 'limit switch -'),
        TACOStates.STOPPED: (status.OK, 'idle or paused'),
        TACOStates.PRESELECTION_REACHED: status.OK,
        TACOStates.DISABLED: status.OK,
        # BUSY states
        # explicit ramp string as there seem to be some inconsistencies
        TACOStates.RAMP: (status.BUSY, 'ramping'),
        TACOStates.MOVING: status.BUSY,
        TACOStates.STOPPING: status.BUSY,
        TACOStates.INIT: (status.BUSY, 'initializing taco device / hardware'),
        TACOStates.RESETTING: status.BUSY,
        TACOStates.STOP_REQUESTED: status.BUSY,
        TACOStates.COUNTING: status.BUSY,
        TACOStates.STARTED: status.BUSY,
        # NOTREACHED states
        TACOStates.UNDEFINED: status.NOTREACHED,
        # WARN states
        TACOStates.ALARM: status.WARN,
        # ERROR states
        TACOStates.FAULT: status.ERROR,
        TACOStates.BLOCKED: status.ERROR,
        TACOStates.TRIPPED: status.ERROR,
        TACOStates.OVERFLOW: status.ERROR,
        TACOStates.OFF: status.ERROR,
        TACOStates.DEVICE_OFF: status.ERROR,
        TACOStates.ON_NOT_REACHED: status.ERROR,
    }

    # the TACO client class to instantiate
    taco_class = None
    # whether to call deviceReset() if the initial switch-on fails
    taco_resetok = True
    # additional TACO error codes mapping to Nicos exception classes
    taco_errorcodes = {}
    # TACO device instance
    _dev = None

    def doPreinit(self, mode):
        if self.loglevel == 'debug':
            self._taco_guard = self._taco_guard_log
        if self.taco_class is None:
            raise ProgrammingError('missing taco_class attribute in class ' +
                                   self.__class__.__name__)
        if mode != SIMULATION:
            self._dev = self._create_client()
        else:
            self._dev = HardwareStub(self)

    def doShutdown(self):
        if self._dev:
            self._dev.disconnectClient()
            del self._dev

    def _setMode(self, mode):
        super()._setMode(mode)
        # remove the TACO device on entering simulation mode, to prevent
        # accidental access to the hardware
        if mode == SIMULATION:
            # keep the device instance around to avoid destruction (which can
            # mess with the TACO connections in the main process if simulation
            # has been forked off)
            self._orig_dev = self._dev
            self._dev = HardwareStub(self)

    def doVersion(self):
        return [(self.tacodevice,
                 self._taco_guard(self._dev.deviceVersion))]

    def doRead(self, maxage=0):
        return self._taco_guard(self._dev.read)

    def doStatus(self, maxage=0):
        for i in range(self.comtries or 1):
            if i:
                session.delay(self.comdelay)
            tacoState = self._taco_guard(self._dev.deviceState)
            if tacoState != TACOStates.FAULT:
                break
        state = self._TACO_STATUS_MAPPING.get(tacoState, status.ERROR)

        if isinstance(state, tuple):
            return state

        statusStr = self._taco_guard(self._dev.deviceStatus)
        return (state, statusStr)

    def doReset(self):
        self._taco_reset(self._dev)

    def doReadUnit(self):
        # explicitly configured unit has precendence
        if 'unit' in self._config:
            return self._config['unit']
        if hasattr(self._dev, 'unit'):
            return self._taco_guard(self._dev.unit)
        return self.parameters['unit'].default

    def doWriteUnit(self, value):
        if hasattr(self._dev, 'setUnit'):
            self._taco_guard(self._dev.setUnit, value)
        if 'unit' in self._config:
            if self._config['unit'] != value:
                self.log.warning('configured unit %r in configuration differs '
                                 'from current unit %r',
                                 self._config['unit'], value)

    def doUpdateTacotimeout(self, value):
        if not self._sim_intercept and self._dev:
            if value != 3.0:
                self.log.warning('%r: client network timeout changed to: '
                                 '%.2f s', self.tacodevice, value)
            self._taco_guard(self._dev.setClientNetworkTimeout, value)

    def doUpdateLoglevel(self, value):
        super().doUpdateLoglevel(value)
        self._taco_guard = value == 'debug' and self._taco_guard_log or \
            self._taco_guard_nolog

    # internal utilities

    def _create_client(self, devname=None, class_=None, resetok=None,
                       timeout=None):
        """Create a new TACO client to the device given by *devname*, using the
        Python class *class_*.  Initialize the device in a consistent state,
        handling eventual errors.

        If no arguments are given, the values of *devname*, *class_*, *resetok*
        and *timeout* are taken from the class attributes *taco_class* and
        *taco_resetok* as well as the device parameters *tacodevice* and
        *tacotimeout*.  This is done during `.doPreinit`, so that you usually
        don't have to call this method in TacoDevice subclasses.

        You can use this method to create additional TACO clients in a device
        implementation that uses more than one TACO device.
        """
        if devname is None:
            devname = self.tacodevice
        if class_ is None:
            class_ = self.taco_class
        if resetok is None:
            resetok = self.taco_resetok
        if timeout is None:
            timeout = self.tacotimeout

        self.log.debug('creating %s TACO device', class_.__name__)

        try:
            dev = class_(devname)
            self._check_server_running(dev)
        except TACOError as err:
            self._raise_taco(err, 'Could not connect to device %r; make sure '
                             'the device server is running' % devname)

        try:
            if timeout != 0:
                if timeout != 3.0:
                    self.log.warning('client network timeout changed to: '
                                     '%.2f s', timeout)
                dev.setClientNetworkTimeout(timeout)
        except TACOError as err:
            self.log.warning('Setting TACO network timeout failed: '
                             '[TACO %d] %s', err.errcode, err)

        try:
            if dev.isDeviceOff():
                dev.deviceOn()
        except TACOError as err:
            self.log.warning('Switching TACO device %r on failed: '
                             '[TACO %d] %s', devname, err.errcode, err)
            try:
                if dev.deviceState() == TACOStates.FAULT:
                    if resetok:
                        dev.deviceReset()
                dev.deviceOn()
            except TACOError as err:
                self._raise_taco(err, 'Switching device %r on after '
                                 'reset failed' % devname)

        return dev

    def _check_server_running(self, dev):
        dev.deviceVersion()

    def _taco_guard_log(self, function, *args):
        """Like _taco_guard(), but log the call."""
        self.log.debug('TACO call: %s%r', function.__name__, args)
        if not self._dev:
            raise NicosError(self, 'TACO Device not initialised')
        with self._com_lock:
            try:
                ret = function(*args)
            except TACOError as err:
                # for performance reasons, starting the loop and querying
                # self.comtries only triggers in the error case
                if self.comtries > 1 or err == DevErr_RPCTimedOut:
                    tries = 2 if err == DevErr_RPCTimedOut and \
                        self.comtries == 1 else self.comtries - 1
                    self.log.warning('TACO %s failed, retrying up to %d times',
                                     function.__name__, tries, exc=1)
                    while True:
                        session.delay(self.comdelay)
                        tries -= 1
                        try:
                            if self.taco_resetok and \
                               self._dev.deviceState() == TACOStates.FAULT:
                                self._dev.deviceInit()
                                session.delay(self.comdelay)
                            ret = function(*args)
                            self.log.debug('TACO return: %r', ret)
                            return ret
                        except TACOError:
                            if tries == 0:
                                break  # and fall through to _raise_taco
                            self.log.warning('TACO %s failed again',
                                             function.__name__, exc=True)
                self.log.debug('TACO exception: %r', err)
                self._raise_taco(err)
            else:
                self.log.debug('TACO return: %r', ret)
                return ret

    def _taco_guard_nolog(self, function, *args):
        """Try running the TACO function, and raise a NicosError on exception.

        A more specific NicosError subclass is chosen if appropriate.  For
        example, database-related errors are converted to
        `.CommunicationError`.
        A TacoDevice subclass can add custom error code to exception class
        mappings by using the `.taco_errorcodes` class attribute.

        If the `comtries` parameter is > 1, the call is retried accordingly.
        """
        if not self._dev:
            raise NicosError(self, 'TACO device not initialised')
        with self._com_lock:
            try:
                return function(*args)
            except TACOError as err:
                # for performance reasons, starting the loop and querying
                # self.comtries only triggers in the error case
                if self.comtries > 1 or err == DevErr_RPCTimedOut:
                    tries = 2 if err == DevErr_RPCTimedOut and \
                        self.comtries == 1 else self.comtries - 1
                    self.log.warning('TACO %s failed, retrying up to %d times',
                                     function.__name__, tries)
                    while True:
                        session.delay(self.comdelay)
                        tries -= 1
                        try:
                            return function(*args)
                        except TACOError:
                            if tries == 0:
                                break  # and fall through to _raise_taco
                self._raise_taco(err, '%s%r' % (function.__name__, args))

    _taco_guard = _taco_guard_nolog

    def _taco_update_resource(self, resname, value):
        """Update the TACO resource *resname* to *value* (both must be strings),
        switching the device off and on.
        """
        if not self._dev:
            raise NicosError(self, 'TACO device not initialised')
        with self._com_lock:
            try:
                self.log.debug('TACO resource update: %s %s', resname, value)
                self._dev.deviceOff()
                self._dev.deviceUpdateResource(resname, value)
                self._dev.deviceOn()
                self.log.debug('TACO resource update successful')
            except TACOError as err:
                self._raise_taco(err, 'While updating %s resource' % resname)

    def _raise_taco(self, err, addmsg=None):
        """Raise a suitable NicosError for a given TACOError instance."""
        tb = sys.exc_info()[2]
        code = err.errcode
        cls = NicosError
        if code in self.taco_errorcodes:
            cls = self.taco_errorcodes[code]
        elif code < 50:
            # error numbers 0-50: RPC call errors
            cls = CommunicationError
        elif 400 <= code < 500:
            # error number 400-499: database system error messages
            cls = CommunicationError
        elif code == DevErr_RangeError:
            cls = LimitError
        elif code in (DevErr_InvalidValue, DevErr_ExecutionDenied):
            cls = InvalidValueError
        elif code in (DevErr_IOError, DevErr_InternalError,
                      DevErr_RuntimeError, DevErr_SystemError):
            cls = CommunicationError
        msg = '[TACO %d] %s' % (err.errcode, err)
        if addmsg is not None:
            msg = addmsg + ': ' + msg
        exc = cls(self, msg, tacoerr=err.errcode)
        raise exc.with_traceback(tb)

    def _taco_reset(self, client, resetcall='deviceReset'):
        try:
            hostname = client.getServerHost()
            servername = client.getServerProcessName()
            personalname = client.getServerPersonalName()
            self.log.info('Resetting TACO device; if this does not help try '
                          'restarting the %s named %s on host %s.',
                          servername, personalname, hostname)
        except AttributeError:  # older version without these API calls
            self.log.info('Resetting TACO device; if this does not help try '
                          'restarting the server.')
        try:
            if resetcall == 'deviceReset':
                self._taco_guard(client.deviceReset)
            else:
                self._taco_guard(client.deviceInit)
        except Exception as err:
            self.log.warning('%s failed with %s', resetcall, err)
        if self._taco_guard(client.isDeviceOff):
            self._taco_guard(client.deviceOn)
