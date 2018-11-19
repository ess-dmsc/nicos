#  -*- coding: utf-8 -*-
# *****************************************************************************
# NICOS, the Networked Instrument Control System of the MLZ
# Copyright (c) 2009-2018 by the NICOS contributors (see AUTHORS)
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

from __future__ import absolute_import, division, print_function

from nicos.core import HasPrecision, MoveError
from nicos.devices.tango import AnalogOutput


class PumpAnalogOutput(HasPrecision, AnalogOutput):
    """Special class for syringe pump outputs that raises an error if the
    requested value could not be infused/withdrawn.
    """

    def doFinish(self):
        pos = self.read(0)
        if not self.isAtTarget(pos):
            raise MoveError(self, 'did not arrive at requested volume, '
                            'check end switches!')
        return False  # don't check again