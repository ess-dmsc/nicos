#  -*- coding: utf-8 -*-
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
#   Artur Glavic <artur.glavic@psi.ch>
#
# *****************************************************************************
from nicos.guisupport.qt import QGraphicsEllipseItem, QGraphicsItem, QGraphicsItemGroup


class InteractiveEllipse(QGraphicsEllipseItem):
    def __init__(self, groupname, *args, **opts):
        QGraphicsEllipseItem.__init__(self, *args, **opts)
        self.setFlag(QGraphicsItem.GraphicsItemFlag.ItemIsSelectable, True)
        self._name = groupname

    def mousePressEvent(self, event):
        self.scene().childSelected(self._name, self)
        QGraphicsEllipseItem.mousePressEvent(self, event)

    def mouseDoubleClickEvent(self, event):
        self.scene().childActivated(self._name, self)
        QGraphicsEllipseItem.mouseDoubleClickEvent(self, event)


class InteractiveGroup(QGraphicsItemGroup):
    def __init__(self, groupname, *args, **opts):
        QGraphicsItemGroup.__init__(self, *args, **opts)
        self.setFlag(QGraphicsItem.GraphicsItemFlag.ItemIsSelectable, True)
        self._name = groupname

    def mousePressEvent(self, event):
        self.scene().childSelected(self._name, self)
        QGraphicsItemGroup.mousePressEvent(self, event)

    def mouseDoubleClickEvent(self, event):
        self.scene().childActivated(self._name, self)
        QGraphicsItemGroup.mouseDoubleClickEvent(self, event)


class TransmittingGroup(QGraphicsItemGroup):
    def __init__(self, *args, **opts):
        QGraphicsItemGroup.__init__(self, *args, **opts)
        self._name = "transmitter"

    def mousePressEvent(self, event):
        for child in self.childItems():
            if type(child) is InteractiveGroup and child.isUnderMouse():
                return child.mousePressEvent(event)
        return QGraphicsItemGroup.mousePressEvent(self, event)

    def mouseDoubleClickEvent(self, event):
        for child in self.childItems():
            if type(child) is InteractiveGroup and child.isUnderMouse():
                return child.mouseDoubleClickEvent(event)
        return QGraphicsItemGroup.mouseDoubleClickEvent(self, event)
