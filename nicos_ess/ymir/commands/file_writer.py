#  -*- coding: utf-8 -*-
# *****************************************************************************
# NICOS, the Networked Instrument Control System of the MLZ
# Copyright (c) 2009-2021 by the NICOS contributors (see AUTHORS)
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
#   AÜC Hardal <umit.hardal@ess.eu>
#
# *****************************************************************************
from nicos import session
from nicos.commands import usercommand
from nicos.core import SIMULATION
from nicos_ess.devices.datasinks.file_writer import FileWriterControl


@usercommand
def start_writing():
    if session.mode == SIMULATION:
        return
    dev = _get_filewriter_control_device()
    dev.doStart()


@usercommand
def stop_writing():
    if session.mode == SIMULATION:
        return
    dev = _get_filewriter_control_device()
    dev.doStop()


def _get_filewriter_control_device():
    # HACK: find the FWC device - perhaps is should be an attached device?
    devs = _find_nicos_devices_by_type(FileWriterControl)
    if not devs:
        session.log.error('Could not find file-writer control device')
        return
    elif len(devs) > 1:
        session.log.error('Found multiple file-writer control devices - ' 
                          'incorrect system configuration? '
                          'Ignoring request')
        return
    return devs[0]


def _find_nicos_devices_by_type(device_type):
    return [dev for dev in session.devices.values()
            if isinstance(dev, device_type)]

