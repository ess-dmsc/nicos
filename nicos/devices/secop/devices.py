#  -*- coding: utf-8 -*-
# *****************************************************************************
# NICOS, the Networked Instrument Control System of the MLZ
# Copyright (c) 2009-2022 by the NICOS contributors (see AUTHORS)
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
#   Markus Zolliker <markus.zolliker@psi.ch>
#
# *****************************************************************************

"""Support for SECoP

This module contains a SecNode device, which represent connections to a SECoP
server, and the base classes SecopDevice, SecopReadable and SecopMoveable.

A SecNodeDevice is connected to a SecNode by assigning the uri value, this
can be done at any time. With auto_create == True, all devices are created
automatically after connections, and they are altered on reconnection.

For a setup for permanent use, with auto_create == False (the default), the
devices are to be created with the class SecopDevice, SecopReadable or
SecopMoveable, and the following parameters:

- secnode: the secnode device name
- secop_module: the name of the remotely connected SECoP module
- params_cfg (optional): a dict {<parameter name>: <cfg dict>}
  if given, only the parameters mentioned as keys are exported.
  The cfg dict may be empty for using the automatically generated attributes:
  description, datainfo, settable, unit and fmtstr.
  The data type must be given as SECoP datainfo converted from json,
  not as NICOS type!
  Attributes given in the cfg dict may overwrite above attributes.
"""

import re
import time
from math import floor, log10
from threading import Event

# pylint: disable=import-error,no-name-in-module
from secop.client import SecopClient
from secop.errors import CommunicationFailedError

from nicos import session
from nicos.core import POLLER, SIMULATION, Attach, DeviceAlias, \
    HasOffset, HasLimits, NicosError, Override, Param, status, usermethod
from nicos.core.device import Device, DeviceMeta, Moveable, Readable
from nicos.core.errors import ConfigurationError
from nicos.core.params import anytype, floatrange, intrange
from nicos.core.utils import formatStatus
from nicos.devices.secop.validators import get_validator, Secop_struct
from nicos.utils import printTable
from nicos.protocols.cache import cache_dump

SECOP_ERROR = 400


class NicosSecopClient(SecopClient):
    def internalize_name(self, name):
        """name mangling

        in order to avoid existing NICOS Moveable attributes
        """
        if name in ('target', 'status', 'stop'):
            return name
        name = super().internalize_name(name).lower()
        prefix, sep, postfix = name.partition('_')
        if prefix not in dir(SecopMoveable):
            return name
        # mangle names matching NICOS device attributes
        # info -> info_, info_ -> info_1, info_1 -> info_2, ...
        if not sep:
            return name + '_'
        if not postfix:
            return name + '_1'
        try:
            num = int(postfix)
            if str(num) == postfix:
                return '%s_%d' % (prefix, num + 1)
        except ValueError:
            pass
        return name


class DefunctDevice(Exception):
    pass


def clean_identifier(anystring):
    return str(re.sub(r'\W+|^(?=\d)', '_', anystring))


def type_name(typ):
    try:
        return typ.__name__
    except AttributeError:
        return typ.__class__.__name__


def get_aliases(dev):
    """get devices aliased to on dev

    return a list containing for each alias a tuple (device, required class).
    """
    # check that the new class fits the required classes on devices self
    # is attached to
    result = []
    for alias in session.devices.values():
        if isinstance(alias, DeviceAlias) and alias.alias == dev.name:
            result.append((alias, alias._cls))
    return result


def get_attaching_devices(dev):
    """get devices attached to dev

    return a list of tuples (device, required class).
    """
    result = []
    for devname in dev._sdevs:
        sdev = session.devices.get(devname)
        if sdev:
            for aname, att in sdev.attached_devices.items():
                if getattr(sdev, '_attached_' + aname, None) == dev:
                    result.append((sdev, att.devclass))
    return result


def class_from_interface(module_properties):
    for ifclass in (module_properties.get('interface_classes', []) or
                    module_properties.get('interface_class', [])):
        try:
            return IF_CLASSES[ifclass.title()]
        except KeyError:
            continue
    return SecopDevice


def secop_base_class(cls):
    """find the first base class from IF_CLASSES in cls"""
    for b in cls.__mro__:
        if b in ALL_IF_CLASSES:
            return b
    raise TypeError('secop_base_class argument must inherit from SecopDevice')


class SecNodeDevice(Readable):
    """SEC node device

    want to have a status -> based on Readable
    """

    parameters = {
        'prefix':      Param("Prefix for the generated devices\n\n"
                             "'$' will be replaced by the equipment id",
                             type=str, default='$_', settable=True),
        'uri':         Param('tcp://<host>:<port>', type=str, settable=True),
        'auto_create': Param('Flag for automatic creation of devices',
                             type=bool, prefercache=False, userparam=False),
        'setup_info':  Param('Setup info', type=anytype, default={},
                             settable=True),
        'visibility_level': Param('level for visibility of created devices',
                                  type=intrange(1, 3), prefercache=False,
                                  default=1, userparam=False),
    }
    parameter_overrides = {
        'unit': Override(default='', mandatory=False),
        # no polling on the SEC node
        'maxage': Override(default=None, userparam=False),
        # SECoP 'pollinterval' would be accessible as 'pollinterval_'
        'pollinterval': Override(default=None, userparam=False),
    }

    valuetype = str
    _secnode = None
    _value = ''
    _status = status.OK, 'unconnected'   # the nicos status
    _devices = {}

    def doPreinit(self, mode):
        self._devices = {}

    def doInit(self, mode):
        if mode == SIMULATION:
            setup_info = self.get_setup_info()
            if self.auto_create:
                self.makeDynamicDevices(setup_info)
            else:
                self._setROParam('setup_info', setup_info)
        elif session.sessiontype != POLLER:
            if self.uri:
                try:
                    self._connect()
                except Exception:
                    pass

    def get_setup_info(self):
        if self._mode == SIMULATION:
            db = session.getSyncDb()
            return db.get('%s/setup_info' % self.name.lower())
        return self.setup_info

    def doRead(self, maxage=0):
        if self._secnode:
            if self._secnode.online:
                self._value = self._secnode.nodename
        else:
            self._value = ''
        return self._value

    def doStatus(self, maxage=0):
        return self._status

    def _set_status(self, code, text):
        self._status = code, text
        if self._cache:
            self._cache.put(self, 'status', self._status)
            self._cache.put(self, 'value', self.doRead())

    def doWriteUri(self, value):
        """change uri and reconnect"""
        # make sure uri is set before reconnect
        self._setROParam('uri', value)
        if self.uri:
            self._connect()
        else:
            self._disconnect()
        return value

    def _connect(self):
        """try to connect

        called on creation and on uri change,
        but NOT on automatic reconnection
        """
        if not self.uri:
            self._disconnect()
        if self._secnode:
            self._secnode.disconnect()
        self._secnode = NicosSecopClient(self.uri, log=self.log)
        self._secnode.register_callback(None, self.nodeStateChange,
                                        self.descriptiveDataChange)
        try:
            self._secnode.connect(10)
            self._set_status(status.OK, 'connected')
            self.createDevices()
            return
        except Exception as e:
            if not isinstance(e, CommunicationFailedError):
                raise
            self.log.warning('can not connect to %s (%s), retry in background',
                             self.uri, e)
            self._set_status(status.ERROR, 'try connecting')
            start_event = Event()
            self._secnode.spawn_connect(start_event.set)

    def _disconnect(self):
        if not self._secnode:
            return
        self.removeDevices()
        self._secnode.disconnect()
        self._set_status(status.OK, 'unconnected')
        self._secnode = None

    def descriptiveDataChange(self, module, description):
        """called when descriptive data changed

        after an automatic reconnection"""
        self.log.warning('node description changed')
        self.createDevices()

    def get_status(self, online, state):
        if not online:
            return status.ERROR, state
        return status.OK if state == 'connected' else status.WARN, state

    def nodeStateChange(self, online, state):
        """called when the state of the connection changes

        'online' is True when connected or reconnecting, False when
                 disconnected or connecting
        'state' is the connection state as a string
        """
        if online and state == 'connected':
            self._set_status(status.OK, 'connected')
            for device in self._devices.values():
                device.setConnected(True)
        elif not online:
            self._set_status(status.ERROR, 'reconnecting')
            for device in self._devices.values():
                device.setConnected(False)
        else:
            self._set_status(status.WARN, state)

    def doShutdown(self):
        self._disconnect()
        if self._devices:
            self.log.error('can not remove devices %s', list(self._devices))

    def _get_prefix(self):
        if not self._secnode:
            return None
        equipment_name = clean_identifier(self._secnode.nodename).lower()
        return self.prefix.replace('$', equipment_name)

    @usermethod
    def showModules(self):
        """show modules of the connected SECoP server

        and intended devices names using the given prefix
        """
        prefix = self._get_prefix()
        if prefix is None:
            self.log.error('secnode is not connected')
            return
        items = [
            (prefix + m, m,
             mod_desc.get(
                 'properties', {}).get('description', '').split('\n')[0])
            for m, mod_desc in self._secnode.modules.items()]
        printTable(['foreseen device name', 'SECoP module', 'description'],
                   items, self.log.info)

    def registerDevice(self, device):
        if not self._secnode:
            raise OSError('unconnected')
        self.log.debug('register %s on %s', device, self)
        self._devices[device.name] = device
        module = device.secop_module
        if module not in self._secnode.modules:
            raise ConfigurationError('no module %r found on this SEC node'
                                     % module)
        for parameter in self._secnode.modules[module]['parameters']:
            updatefunc = getattr(device, '_update_' + parameter,
                                 device._update)
            self._secnode.register_callback((module, parameter),
                                            updateEvent=updatefunc)
            try:
                data = self._secnode.cache[module, parameter]
                if data:
                    updatefunc(module, parameter, *data)
                else:
                    self.log.warning('No data for %s:%s', module, parameter)
            except KeyError:
                self.log.warning('No cache for %s:%s', module, parameter)

    def unregisterDevice(self, device):
        self.log.debug('unregister %s from %s', device, self)
        session.configured_devices.pop(device.name, None)
        if self._devices.pop(device.name, None) is None:
            self.log.info('device %s already removed', device.name)
            return
        module = device.secop_module
        try:
            moddesc = self._secnode.modules[module]
        except KeyError:  # do not complain again about missing module
            return
        for parameter in moddesc['parameters']:
            updatefunc = getattr(device, '_update_' + parameter,
                                 device._update)
            self._secnode.unregister_callback((module, parameter),
                                              updateEvent=updatefunc)

    def createDevices(self):
        """create drivers and devices

        for the devices to be created from the connected SECoP server
        """
        if not self._secnode:
            self.log.error('secnode is not connected')
            return
        prefix = self._get_prefix()
        setup_info = {}
        for module, mod_desc in self._secnode.modules.items():
            module_properties = mod_desc.get('properties', {})
            kwds = {
                'secop_properties': module_properties,
            }
            # convert parameters and command description to the needed items,
            # especially avoid datatype or a nicos type here,
            # as this would need pickle to put into the cache.
            # datainfo is no problem
            params_cfg = {}
            for pname, props in mod_desc['parameters'].items():
                datainfo = props['datainfo']
                pargs = dict(datainfo=datainfo, description=props['description'])
                if not props.get('readonly', True) and pname != 'target':
                    pargs['settable'] = True
                unit = datainfo.get('unit', '')
                fmtstr = None
                if datainfo['type'] == 'double':
                    fmtstr = datainfo.get('fmtstr', '%g')
                elif datainfo['type'] == 'scaled':
                    fmtstr = datainfo.get(
                        'fmtstr', '%%.%df' %
                                  max(0, -floor(log10(datainfo['scale']))))
                if unit:
                    pargs['unit'] = unit
                if pname == 'target':
                    kwds['target_datainfo'] = datainfo
                    pargs['datainfo'] = None
                elif pname == 'value':
                    kwds['unit'] = unit
                    if fmtstr is not None:
                        kwds['fmtstr'] = fmtstr
                    else:
                        kwds['fmtstr'] = '%r'
                    kwds['value_datainfo'] = datainfo
                if pname not in ('status', 'value'):
                    if fmtstr is not None and fmtstr != '%g':
                        pargs['fmtstr'] = fmtstr
                    params_cfg[pname] = pargs
            commands_cfg = {
                cname: {'description': props.get('description', ''),
                        'datainfo': props['datainfo']}
                for cname, props in mod_desc['commands'].items()}
            cls = class_from_interface(module_properties)
            if isinstance(cls, SecopReadable):
                kwds.setdefault('unit', '')  # unit is mandatory on Readables
            if module_properties.get('visibility', 1) > self.visibility_level:
                kwds['visibility'] = ()
            desc = dict(secnode=self.name,
                        description=mod_desc.get('properties', {}).get(
                            'description', ''),
                        secop_module=module,
                        params_cfg=params_cfg,
                        commands_cfg=commands_cfg,
                        **kwds)
            # the following test may be removed later, when no bugs appear ...
            if 'cache_unpickle("' in cache_dump(desc):
                self.log.error('module %r skipped - setup info needs pickle', module)
            else:
                setup_info[prefix + module] = (
                    'nicos.devices.secop.devices.%s' % cls.__name__, desc)
        if not setup_info:
            self.log.info('creating devices for %s skipped', self.name)
            return
        if self.auto_create:
            self.makeDynamicDevices(setup_info)
        else:
            self._setROParam('setup_info', setup_info)

    def removeDevices(self):
        self.makeDynamicDevices({})

    def makeDynamicDevices(self, setup_info):
        """create and destroy dynamic devices

        create devices from setup_info, and store the name of the setup
        creating the creator device in session.creator_devices for
        session.getSetupInfo()
        Based on the previous setup_info from self.setup_info,
        devices are created, recreated, destroyed or remain unchanged.
        If setup_info is empty, destroy all devices.
        """
        prevdevices = set(self.setup_info.keys())
        self._setROParam('setup_info', setup_info)

        # find setup of this secnode
        result = session.getSetupInfo()
        setupname = None  # only to avoid undefined-loop-variable later
        for setupname in session.loaded_setups:
            info = result.get(setupname, None)
            if info and self.name in info['devices']:
                break
        else:
            raise ConfigurationError('can not find setup')
        # add new or changed devices
        for devname, devcfg in setup_info.items():
            prevdevices.discard(devname)
            dev = session.devices.get(devname, None)
            if dev:
                if not isinstance(dev, SecopDevice) or (
                        dev._attached_secnode and
                        dev._attached_secnode != self):
                    self.log.error('device %s already exists', devname)
                    continue
                base = secop_base_class(dev.__class__)
                prevcfg = (base.__module__ + '.' + base.__name__,
                           dict(secnode=self.name, **dev._config))
            else:
                prevcfg = None
            session.configured_devices[devname] = devcfg
            session.dynamic_devices[devname] = setupname
            if prevcfg == devcfg:
                if dev._defunct:
                    dev.setAlive(self)
            else:
                if dev is None:
                    # add new device
                    session.createDevice(devname, recreate=True, explicit=True)
                    dev = session.devices[devname]
                else:
                    # modify existing device
                    if dev._attached_secnode:
                        dev._attached_secnode.unregisterDevice(dev)
                    try:
                        dev.replaceClass(devcfg[1])
                        dev.setAlive(self)
                    except ConfigurationError:
                        # above failed because an alias or attaching device
                        # requires a specific class.
                        # make old device defunct and replace by a new device
                        session.destroyDevice(dev)
                        session.dynamic_devices.pop(devname, None)
                        session.createDevice(devname, recreate=True,
                                             explicit=True)
                        prevdevices.discard(devname)
                        dev = session.devices[devname]
                if not isinstance(dev, SecopReadable):
                    # we will not get status updates for these
                    dev.updateStatus()

        defunct = set()
        # defunct devices no longer available
        for devname in prevdevices:
            dev = session.devices.get(devname)
            if dev is None or dev._attached_secnode != self:
                continue
            # do not consider temporary devices
            sdevs = [att for att in dev._sdevs if att in session.devices]
            if sdevs:
                self.log.warning('defunct device is attached to %s',
                                 ', '.join(sdevs))
            dev.setDefunct()
            defunct.add(devname)

        # inform client that setups have changed
        session.setupCallback(list(session.loaded_setups),
                              list(session.explicit_setups))


class SecopDevice(Device):
    # based on Readable instead of Device, as we want to have a status
    attached_devices = {
        'secnode': Attach('sec node', SecNodeDevice),
    }
    parameters = {
        'secop_module': Param('SECoP module', type=str, settable=False,
                              userparam=False),
        'secop_properties': Param('SECoP module properties',
                                  type=anytype, settable=False,
                                  userparam=False),
    }
    STATUS_MAP = {
        0: status.DISABLED,
        1: status.OK,
        2: status.WARN,
        3: status.BUSY,
        4: status.ERROR,
    }
    _defunct = False
    _cache = None

    @classmethod
    def makeDevClass(cls, name, **config):
        """create a class with the needed doRead/doWrite methods

        for accessing the assigned SECoP module
        """
        secnodedev = session.getDevice(config['secnode'])
        params_override = config.pop('params_cfg', None)
        commands_override = config.pop('commands_cfg', None)
        setup_info = secnodedev.get_setup_info()
        if name in setup_info:
            devcfg = dict(setup_info[name][1])
            params_cfg = dict(devcfg.pop('params_cfg'))
            commands_cfg = dict(devcfg.pop('commands_cfg'))
        else:
            devcfg, params_cfg, commands_cfg = {}, {}, {}
        if params_override is not None:
            for pname, pdict in list(params_cfg.items()):
                pnew = params_override.get(pname)
                if pnew is not None:
                    params_cfg[pname] = dict(pdict, **pnew)
                elif pname not in cls.parameters:
                    params_cfg.pop(pname)  # remove parameters not mentioned
        if commands_override is not None:
            for cname, cmddict in list(commands_cfg.items()):
                cnew = commands_override.get(cname)
                if cnew is not None:
                    commands_cfg[cname] = dict(cmddict, **cnew)
                else:
                    commands_cfg.pop(cname)  # remove commands not mentioned
        devcfg.update(config)

        parameters = {}
        # create parameters and methods
        attrs = dict(parameters=parameters, __module__=cls.__module__)
        if 'target_datainfo' in config:
            attrs['valuetype'] = get_validator(config.pop('target_datainfo'))
        if 'value_datainfo' in config:
            attrs['_maintype'] = staticmethod(get_validator(config.pop('value_datainfo')))
        for pname, kwargs in params_cfg.items():
            typ = get_validator(kwargs.pop('datainfo'))
            if 'fmtstr' not in kwargs and (typ is float or
                                           isinstance(typ, floatrange)):
                # the fmtstr default differs in SECoP and NICOS
                # copy kwargs as it may be read only
                kwargs = dict(kwargs, fmtstr='%g')
            parameters[pname] = Param(volatile=True, type=typ, **kwargs)

            if pname == 'target':
                continue  # special treatment of target in SecopWritable.doReadTarget

            def do_read(self, maxage=None, pname=pname, validator=typ):
                return self._read(pname, maxage, validator)

            attrs['doRead%s' % pname.title()] = do_read

            if kwargs.get('settable', False):
                if isinstance(typ, Secop_struct):
                    typ = typ.write_validator

                def do_write(self, value, pname=pname, validator=typ):
                    return self._write(pname, value, validator)

                attrs['doWrite%s' % pname.title()] = do_write

        for cname, cmddict in commands_cfg.items():

            def makecmd(cname, datainfo, description):
                argument = datainfo.get('argument')
                # we ignore the result type here (no need to check)
                optional = datainfo.get('optional', ())

                if argument is None:
                    help_arglist = ''

                    def cmd(self):
                        return self._call(cname, None)

                elif argument['type'] == 'tuple':
                    # treat tuple elements as separate arguments
                    help_arglist = ', '.join('<%s>' % type_name(get_validator(t))
                                             for t in argument['members'])

                    def cmd(self, *args):
                        return self._call(cname, args)

                elif argument['type'] == 'struct':
                    # treat SECoP struct as keyworded arguments
                    # varargs will be treated in the order from the dictwith
                    # original order is kept only in Py >= 3.6
                    # however, it will correspond to the order in help_arglist
                    keys = list(argument['members'])
                    if optional is True:
                        optional = keys
                    for key in optional:
                        keys.remove(key)
                    help_arglist = ', '.join(keys + ['%s=None' % k
                                                     for k in optional])
                    keys.extend(optional)

                    def cmd(self, *args, keys_=tuple(keys), **kwds):
                        if len(args) > len(keys_):
                            raise ValueError('too many arguments')
                        for arg, key in zip(args, keys_):
                            if key in kwds:
                                raise ValueError(
                                    'got multiple values for argument %r'
                                    % key)
                            kwds[key] = arg
                        return self._call(cname, kwds)

                else:
                    argtype = get_validator(argument)
                    help_arglist = '<%s>' % type_name(argtype) if argtype \
                                   else ''

                    def cmd(self, argument=None):
                        return self._call(cname, argument)

                cmd.help_arglist = help_arglist
                cmd.__doc__ = description
                cmd.__name__ = cname
                return cmd

            old = getattr(cls, cname, None)
            if old is None:
                attrs[cname] = usermethod(makecmd(cname, **cmddict))
            elif cname != 'stop':
                # stop is handled separately, do not complain
                session.log.warning(
                    'skip command %s, as it would overwrite method of %r', cname, cls.__name__)

        classname = cls.__name__ + '_' + name
        # create a new class extending SecopDevice, apply DeviceMeta in order
        # to include the added parameters
        features = config['secop_properties'].get('features', [])
        mixins = tuple(FEATURES[f] for f in features if f in FEATURES)
        if mixins:
            # create class to hold access methods
            newclass = DeviceMeta.__new__(DeviceMeta, classname + '_base', (cls,), attrs)
            # create class with mixins, with methods potentially overriding access methods
            newclass = DeviceMeta.__new__(DeviceMeta, classname, mixins + (newclass,), {})
        else:
            newclass = DeviceMeta.__new__(DeviceMeta, classname, (cls,), attrs)
        newclass._modified_config = devcfg  # store temporarily for __init__
        return newclass

    def __new__(cls, name, **config):
        """called when an instance of the class is created but before __init__

        instead of returning a SecopDevice, we create an object of an extended
        class here
        """
        newclass = cls.makeDevClass(name, **config)
        return Readable.__new__(newclass)

    def __init__(self, name, **config):
        """apply modified config"""
        self._attached_secnode = None
        Device.__init__(self, name, **self._modified_config)
        del self.__class__._modified_config

    def replaceClass(self, config):
        """replace the class on the fly

        happens when the structure for the device has changed
        """
        cls = class_from_interface(config['secop_properties'])
        newclass = cls.makeDevClass(self.name, **config)
        bad_attached = False
        for dev, cls in get_attaching_devices(self):
            if issubclass(newclass, cls):
                self.log.warning('reattach %s to %s', dev.name, self.name)
            else:
                self.log.error('can not attach %s to %s', dev.name, self.name)
                bad_attached = True
        if bad_attached:
            raise ConfigurationError('device class mismatch')
        for dev, cls in get_aliases(self):
            if issubclass(newclass, cls):
                self.log.warning('redirect alias %s to %s',
                                 dev.name, self.name)
            else:
                self.log.error('release alias %s from %s', dev.name, self.name)
                dev.alias = ''
        self.__class__ = newclass
        # as we do not go through self.__init__ again,
        # we have to update self._config
        self._config = dict((name.lower(), value)
                            for (name, value) in config.items())
        for aname in self.attached_devices:
            self._config.pop(aname, None)

    def doPreinit(self, mode):
        if mode != SIMULATION:
            self._attached_secnode.registerDevice(self)

    def _update(self, module, parameter, value, timestamp, readerror):
        if parameter not in self.parameters:
            return
        if readerror:
            if self._cache:
                self._cache.invalidate(self, parameter)
            return
        try:
            # ignore timestamp for now
            self._setROParam(parameter, value)
        except Exception as err:
            self.log.error('%r', err)
            self.log.error('can not set %s:%s to %r', module, parameter, value)

    def _defunct_error(self):
        if session.devices.get(self.name) == self:
            return DefunctDevice('SECoP device %s no longer available'
                                 % self.name)
        return DefunctDevice('refers to a replaced defunct SECoP device %s'
                             % self.name)

    def _read(self, param, maxage, validator):
        try:
            secnode = self._attached_secnode._secnode
        except AttributeError:
            raise self._defunct_error() from None
        if not secnode.online:
            raise NicosError('no SECoP connection')
        value, timestamp, readerror = secnode.cache[self.secop_module, param]
        if readerror:
            raise NicosError(str(readerror)) from None
        if maxage is not None and time.time() > (timestamp or 0) + maxage:
            value = secnode.getParameter(self.secop_module, param)[0]
        value = validator(value)
        return value

    def _write(self, param, value, validator):
        try:
            value = validator(value)
            self._attached_secnode._secnode.setParameter(self.secop_module,
                                                         param, value)
            return value
        except AttributeError:
            raise self._defunct_error() from None

    def _call(self, cname, argument=None):
        return self._attached_secnode._secnode.execCommand(
            self.secop_module, cname, argument)[0]

    def setDefunct(self):
        if self._defunct:
            self.log.warning('device is already defunct')
            return
        self._defunct = True
        if self._attached_secnode is not None:
            self._attached_secnode.unregisterDevice(self)
            # make defunct
            self._attached_secnode = None
            self.updateStatus()
            self._cache = None
        self.updateStatus()

    def setAlive(self, secnode):
        self._defunct = False
        self._cache = secnode._cache
        self._attached_secnode = secnode
        secnode.registerDevice(self)
        # clear defunct status
        self.updateStatus()

    def doShutdown(self):
        if not self._defunct:
            self.setDefunct()

    def doStatus(self, maxage=0):
        if not self._attached_secnode:
            return status.ERROR, 'defunct'
        if not self._attached_secnode._secnode.online:
            return status.ERROR, 'no SECoP connection'
        return status.OK, ''

    def updateStatus(self):
        """get the status and update status in cache"""
        # even when not a Readable, the status in the cache is updated
        # and appears in the device panel
        if self._cache:
            self._cache.put(self, 'status', self.doStatus())

    def setConnected(self, connected):
        if not connected:
            if self._cache:
                self._cache.clear(self, ['status'])
        self.updateStatus()


class SecopReadable(SecopDevice, Readable):
    parameter_overrides = {
        # do not force to give unit in setup file
        # (take from SECoP description)
        'unit': Override(default='', mandatory=False),
        # maxage and pollinterval are unused as polling is done remotely
        'maxage': Override(default=None, userparam=False),
        'pollinterval': Override(default=None, userparam=False),
    }
    _maintype = staticmethod(anytype)

    def doRead(self, maxage=0):
        try:
            return self._read('value', maxage, self._maintype)
        except NicosError:
            st = self.doStatus()
            if st[0] in (status.DISABLED, status.ERROR):
                raise NicosError(st[1]) from None
            raise

    def doStatus(self, maxage=0):
        code, text = SecopDevice.doStatus(self)
        if code != status.OK:
            return code, text
        cached = self._attached_secnode._secnode.cache.get(
            (self.secop_module, 'status'))
        if not cached:
            return code, text
        value, _, readerror = cached
        if value is None:
            code, text = SECOP_ERROR, str(readerror)
        else:
            code, text = value
        if 390 <= code < 400:  # SECoP status finalizing
            return status.OK, text
        # treat SECoP code 401 (unknown) as error - should be distinct from
        # NICOS status unknown
        return self.STATUS_MAP.get(code // 100, status.UNKNOWN), text

    def _update_status(self, module, parameter, value, timestamp, readerror):
        self.updateStatus()

    def _update_value(self, module, parameter, value, timestamp, readerror):
        if readerror:
            if self._cache:
                self._cache.invalidate(self, 'value')
            return
        if self._cache:
            try:
                # convert enum code to name
                value = self._maintype(value)
            except Exception:
                pass
            self._cache.put(self, 'value', value)

    def info(self):
        # override the default NICOS behaviour here:
        # a disabled SECoP module should be ignored silently
        st = self.status()
        if st[0] == status.DISABLED:
            # do not display info in data file when disabled
            return []
        if st[0] == status.ERROR:
            # avoid calling read()
            return [('value', None, 'Error: %s' % st[1], '', 'general'),
                    ('status', st, formatStatus(st), '', 'status')]
        return Readable.info(self)


class SecopWritable(SecopReadable, Moveable):

    def doReadTarget(self, maxage=None):
        try:
            return self._read('target', maxage, anytype)
        except NicosError:
            # this might happen when the target is not initialized
            # if we do not catch here, Moveable.start will raise
            # when comparing with the previous value
            return None

    def doStart(self, target):
        try:
            self._attached_secnode._secnode.setParameter(
                self.secop_module, 'target', target)
        except AttributeError:
            raise self._defunct_error() from None


class SecopMoveable(SecopWritable):

    def doStop(self):
        if self.status(0)[0] == status.BUSY:
            try:
                self._attached_secnode._secnode.execCommand(
                    self.secop_module, 'stop')
            except Exception as e:
                self.log.error('error while stopping: %r', e)
                self.updateStatus()


class SecopHasOffset(HasOffset):
    """modified HasOffset mixin

    goal: make the class to be accepted by the adjust command
    """

    def doWriteOffset(self, value):
        # remark: possible adjustments of limits, targets have to be done
        # in the remote implementation
        self._write('offset', value, float)


class SecopHasLimits(HasLimits):
    """modifed HasLimits mixin

    match the proposed SECoP feature HasOffset, with a limits parameter
    corresponding to userlimits and the abslimits module _property_
    """
    parameter_overrides = {
        'abslimits': Override(default=(-9e99, 9e99), prefercache=False),
        'userlimits': Override(default=(-9e99, 9e99), volatile=True),
        'limits': Override(userparam=False),
    }

    def doPreinit(self, mode):
        super().doPreinit(mode)
        if mode != SIMULATION:
            self._config['abslimits'] = self.secop_properties.get('abslimits', (-9e99, 9e99))

    def doReadUserlimits(self):
        return self.limits

    def doWriteUserlimits(self, value):
        self.limits = value
        return self.limits


IF_CLASSES = {
    'Drivable': SecopMoveable,
    'Writable': SecopWritable,
    'Readable': SecopReadable,
    'Module': SecopDevice,
}

ALL_IF_CLASSES = set(IF_CLASSES.values())

FEATURES = {
    'HasLimits': SecopHasLimits,
    'HasOffset': SecopHasOffset,
}