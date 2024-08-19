# *****************************************************************************
# NICOS, the Networked Instrument Control System of the MLZ
# Copyright (c) 2009-2019 by the NICOS contributors (see AUTHORS)
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
from nicos.core.status import BUSY
from nicos.guisupport.qt import (
    QColor,
    QFont,
    QGraphicsEllipseItem,
    QGraphicsItem,
    QGraphicsRectItem,
    QGraphicsScene,
    QGraphicsSimpleTextItem,
    Qt,
)
from nicos.protocols.cache import OP_TELL, cache_dump, cache_load

from nicos_ess.estia.gui.panels.custom_controls import (
    InteractiveEllipse,
    InteractiveGroup,
    TransmittingGroup,
)


class RobotScene(QGraphicsScene):
    def __init__(self, parent, client, options):
        QGraphicsScene.__init__(self, parent)
        self.client = client
        self._currentSelection = None
        self.posx = options.get("posx")
        self.posz = options.get("posz")
        self.approach1 = options.get("approach1")
        self.rotation1 = options.get("rotation1")
        self.approach2 = options.get("approach2")
        self.rotation2 = options.get("rotation2")
        self.selene = int(options.get("selene", 1))
        self.robot = options.get("robot", None)
        self.offsetx = float(options.get("offsetx"))
        self.offsetz = float(options.get("offsetz"))
        self.screw_group = options.get("screw_group")

        self.build_background()
        self.build_cart()

        client.cache.connect(self.on_client_cache)
        client.connected.connect(self.on_client_connected)

    def build_background(self):
        rack = QGraphicsRectItem(-7250, 0, 7250, 820)
        rack.setZValue(-13.0)
        rack.setBrush(QColor(200, 200, 200))
        self.addItem(rack)

        stage = self.addRect(-7250, -50, 7250, 100)
        stage.setZValue(-11.0)
        stage.setBrush(QColor(50, 50, 50))

        for group in range(15):
            for sx, sy, active, item in self.screw_group:
                si = InteractiveEllipse("screw", -sx - 480 * group, 720 - sy, 30, 30)
                si.screw_group = 15 - group
                si.screw_item = item + 1
                self.addItem(si)
                si.setZValue(-10.0)
                if active:
                    si.setBrush(QColor(100, 25, 25))
                else:
                    si.setBrush(QColor(75, 75, 75))
                si.setFlag(QGraphicsItem.GraphicsItemFlag.ItemIsSelectable, True)

            group_label = QGraphicsSimpleTextItem("%01i" % (si.screw_group))
            group_label.setFont(QFont("sans", 52))
            self.addItem(group_label)
            group_label.setPos(-(260 + 480 * group), 375)

            cutout = QGraphicsRectItem(-(380 + 480 * group), 220, 300, 540)
            self.addItem(cutout)
            cutout.setZValue(-12.0)
            cutout.setBrush(QColor(150, 150, 150))

    def build_cart(self):
        self.vstage = TransmittingGroup()
        v = self.vstage
        v.setZValue(10.0)
        self.addItem(v)

        vstage = QGraphicsRectItem(-100, 0, 200, 820)
        vstage.setZValue(-1.0)
        vstage.setBrush(QColor(128, 128, 128, 128))
        v.addToGroup(vstage)

        self.hstage = InteractiveGroup("driver")
        h = self.hstage
        h.setZValue(12.0)
        v.addToGroup(h)

        hstage = QGraphicsRectItem(-160, -60, 320, 120)
        hstage.setZValue(-1.0)
        hstage.setBrush(QColor(128, 128, 128, 128))
        h.addToGroup(hstage)

        self.driver2 = QGraphicsEllipseItem(-204, -25, 50, 50)
        self.driver2.setZValue(1.0)
        self.driver2.setBrush(QColor(128, 128, 128, 128))
        h.addToGroup(self.driver2)
        self.driver1 = QGraphicsEllipseItem(154, -25, 50, 50)
        self.driver1.setZValue(1.0)
        self.driver1.setBrush(QColor(128, 128, 128, 128))
        h.addToGroup(self.driver1)

        rot_center1 = InteractiveGroup("rot1")
        self.rotind1 = QGraphicsRectItem(-5, -55, 10, 60)
        self.rotind1.setZValue(2.0)
        self.rotind1.setBrush(QColor(150, 0, 0))
        rot_center1.addToGroup(self.rotind1)
        h.addToGroup(rot_center1)

        rot_center2 = InteractiveGroup("rot2")
        self.rotind2 = QGraphicsRectItem(-5, -55, 10, 60)
        self.rotind2.setZValue(2.0)
        self.rotind2.setBrush(QColor(150, 0, 0))
        rot_center2.addToGroup(self.rotind2)
        h.addToGroup(rot_center2)

        v.setPos(-3500, 0)
        h.setPos(0, -150)
        rot_center1.setPos(179, 0)
        rot_center2.setPos(-179, 0)

    def on_client_cache(self, data):
        (time, key, op, value) = data
        if "/" not in key:
            return
        ldevname, subkey = key.rsplit("/", 1)

        if ldevname == self.posx and subkey == "value":
            value = cache_load(value)
            value = value - 7250
            self.vstage.setPos(value + self.offsetx, 0)
        elif ldevname == self.posz and subkey == "value":
            value = cache_load(value)
            self.hstage.setPos(0, 800 - value - self.offsetz)
        elif ldevname == self.rotation1 and subkey == "value":
            value = cache_load(value)
            if self.selene == 1:
                self.rotind1.setRotation(-value)
            else:
                self.rotind1.setRotation(value)
        elif ldevname == self.rotation2 and subkey == "value":
            value = cache_load(value)
            if self.selene == 1:
                self.rotind2.setRotation(-value)
            else:
                self.rotind2.setRotation(value)
        elif ldevname == self.approach1 and subkey == "status":
            status_id, text = cache_load(value)
            if status_id == BUSY:
                self.driver1.setBrush(QColor(200, 200, 64, 200))
                self.rotind1.setBrush(QColor(200, 200, 0))
            elif text.strip() in ["HexScrewFullyOut", "InterlockBwd"]:
                self.driver1.setBrush(QColor(64, 64, 128, 200))
                self.rotind1.setBrush(QColor(150, 0, 0))
            elif text.strip() == "HexScrewInserted":
                self.driver1.setBrush(QColor(64, 255, 64, 200))
                self.rotind1.setBrush(QColor(0, 255, 0))
            else:
                self.driver1.setBrush(QColor(255, 64, 64, 200))
                self.rotind1.setBrush(QColor(255, 0, 0))
        elif ldevname == self.approach2 and subkey == "status":
            status_id, text = cache_load(value)
            if status_id == BUSY:
                self.driver2.setBrush(QColor(200, 200, 64, 200))
                self.rotind2.setBrush(QColor(200, 200, 0))
            elif text.strip() in ["HexScrewFullyOut", "InterlockBwd"]:
                self.driver2.setBrush(QColor(64, 64, 128, 200))
                self.rotind2.setBrush(QColor(150, 0, 0))
            elif text.strip() == "HexScrewInserted":
                self.driver2.setBrush(QColor(64, 255, 64, 200))
                self.rotind2.setBrush(QColor(0, 255, 0))
            else:
                self.driver2.setBrush(QColor(255, 64, 64, 200))
                self.rotind2.setBrush(QColor(255, 0, 0))

    def on_client_connected(self):
        state = self.client.ask("getstatus")
        if not state:
            return
        devlist = [
            self.posx,
            self.posz,
            self.approach1,
            self.rotation1,
            self.approach2,
            self.rotation2,
        ]

        for devname in devlist:
            self._create_device_item(devname)

    def _create_device_item(self, devname):
        ldevname = devname.lower()
        # get all cache keys pertaining to the device
        params = self.client.getDeviceParams(devname)
        if not params:
            return

        # let the cache handler process all properties
        for key, value in params.items():
            self.on_client_cache((0, ldevname + "/" + key, OP_TELL, cache_dump(value)))

    def resizeEvent(self, value=None):
        self._view.fitInView(self.sceneRect(), mode=Qt.AspectRatioMode.KeepAspectRatio)

    def childSelected(self, name, item=None):
        self._currentSelection = name
        if hasattr(item, "screw_group"):
            self.parent().lblRobotSelection.setText(
                f"item={item.screw_item}, " f"group={item.screw_group}"
            )

    def childActivated(self, name, item):
        if hasattr(item, "screw_group") and self.robot and item.screw_item > 0:
            # move to activated screw location
            self.client.tell(
                "queue",
                f"Moving to Screw ({item.screw_item}," f"{item.screw_group})",
                f"maw({self.robot}, ({item.screw_item},"
                f"{item.screw_group}))\n{self.robot}.engage()",
            )
