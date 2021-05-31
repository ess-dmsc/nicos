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
from nicos.guisupport.qt import QDoubleValidator, QValidator


class DoubleValidator(QDoubleValidator):

    def __init__(self, bottom, top, decimal=0):
        QDoubleValidator.__init__(self)

        # Required to handle manual float validation
        self.maximum_value = top
        self.minimum_value = bottom
        self.decimal_precision = decimal

        self.setNotation(QDoubleValidator.StandardNotation)
        self.setRange(bottom, top, decimal)  # Required for standard validation

    def validate(self, string, pos):
        # We need to add this to have a successful float casting.
        if string == "":
            return QValidator.Intermediate, string, pos
        """
        Here we make sure to use `.` in floats instead of `,` which 
        QValidator expects. Try-except block prevents string-types after
        `.` via float casting. That is, 
        
            >> if '.' in string:
                   return QValidator.Intermediate, string, pos
                
        leads acceptable values like
        
            >> 12.sdaad12r..asf-dsfs1*,
            
        which are of course invalid. 
        """
        if '.' in string:
            try:
                if self.maximum_value > float(string) > self.minimum_value:
                    return QValidator.Acceptable, string, pos
            except ValueError:
                return QValidator.Invalid, string, pos
            finally:
                if len(string.split('.')[1]) > self.decimal_precision:
                    return QValidator.Invalid, string, pos

        # Handle ranges in the absence of `.`, separately.
        try:
            if float(string) > self.maximum_value\
                    or self.minimum_value > float(string):
                return QValidator.Invalid, string, pos
        except ValueError:
            return QValidator.Invalid, string, pos

        return QDoubleValidator.validate(self, string, pos)

