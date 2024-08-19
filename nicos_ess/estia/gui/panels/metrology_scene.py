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
import numpy as np

from nicos.core.status import BUSY, DISABLED, ERROR, NOTREACHED, OK, UNKNOWN, WARN
from nicos.guisupport.qt import (
    QColor,
    QFont,
    QGraphicsEllipseItem,
    QGraphicsRectItem,
    QGraphicsScene,
    QGraphicsSimpleTextItem,
    QPen,
    QPointF,
    QPolygonF,
)
from nicos.protocols.cache import OP_TELL, cache_dump, cache_load

from nicos_ess.estia.gui.panels.custom_controls import (
    InteractiveGroup,
    TransmittingGroup,
)

STATUS_COLORS = {
    OK: QColor(0, 150, 0),
    WARN: QColor(100, 100, 0),
    BUSY: QColor(50, 50, 0),
    NOTREACHED: QColor(100, 0, 100),
    DISABLED: QColor(0, 0, 0),
    ERROR: QColor(150, 0, 0),
    UNKNOWN: QColor(0, 0, 0),
}


class MetrologyScene(QGraphicsScene):
    def __init__(self, parent, client, options):
        QGraphicsScene.__init__(self, parent)
        self.client = client
        self.channels = list(options.get("channels"))
        self.positions = list(options.get("positions"))
        self.selene = int(options.get("selene", 1))
        self.cart_position = str(options.get("cart_position"))
        self.offsetx = float(options.get("offsetx", 0))
        self._currentSelection = None
        self.collimators = {}
        self.mirrors_H = {}
        self.mirrors_V = {}
        self.cart = TransmittingGroup()

        self._draw_selene_scene()
        self._draw_mirrors()
        self._draw_cart()

        client.cache.connect(self.on_client_cache)
        client.connected.connect(self.on_client_connected)

    def _draw_selene_scene(self):
        stone = QGraphicsRectItem(0, -475, 7250, 950)
        stone.setZValue(-12.0)
        stone.setBrush(QColor(50, 50, 50))
        self.addItem(stone)

        indent = self.addRect(0, -250, 7250, 500)
        indent.setZValue(-11.0)
        indent.setBrush(QColor(255, 255, 255, 50))

        refsurf = self.addRect(0, -280, 7250, 30)
        refsurf.setZValue(-11.0)
        refsurf.setBrush(QColor(50, 50, 150, 100))

        refsurf = self.addRect(0, 220, 7250, 30)
        refsurf.setZValue(-11.0)
        refsurf.setBrush(QColor(50, 50, 150, 100))

        rail = self.addRect(0, -320, 7250, 30)
        rail.setZValue(-10.0)
        rail.setBrush(QColor(250, 250, 250))

        rail = self.addRect(0, 290, 7250, 30)
        rail.setZValue(-10.0)
        rail.setBrush(QColor(250, 250, 250))

        toppos, toptxt = self._draw_horizontal_collimator(self.positions[0], False)
        self.addItem(toppos)
        toppos.setPos(7210, -220)
        botpos, bottxt = self._draw_horizontal_collimator(self.positions[1], True)
        self.addItem(botpos)
        botpos.setPos(7210, 220)
        self.collimators[self.positions[0]] = (toppos, toptxt)
        self.collimators[self.positions[1]] = (botpos, bottxt)

        topline = self.addLine(500, -220, 7210, -220)
        topline.setZValue(-5.0)
        topline.setPen(QPen(QColor(255, 50, 50, 150), 5))

        botline = self.addLine(500, 220, 7210, 220)
        botline.setZValue(-5.0)
        botline.setPen(QPen(QColor(255, 50, 50, 150), 5))

        self.collimator_lines = [topline, botline]

    def _draw_horizontal_collimator(self, label, text_above=True):
        group = InteractiveGroup(label)
        outer = QGraphicsRectItem(-6, -6, 24, 12)
        outer.setBrush(STATUS_COLORS[UNKNOWN])
        group.addToGroup(outer)
        inner = QGraphicsRectItem(12, -3, 14, 6)
        inner.setBrush(STATUS_COLORS[UNKNOWN])
        group.addToGroup(inner)
        text = QGraphicsSimpleTextItem("0")
        text.setFont(QFont("sans", 24))
        group.addToGroup(text)
        title = QGraphicsSimpleTextItem(label)
        title.setFont(QFont("sans", 26, QFont.Weight.Bold))
        if text_above:
            title.setPos(-100, -80)
            text.setPos(-100, -48)
        else:
            title.setPos(-100, 20)
            text.setPos(-100, 62)
        group.addToGroup(title)
        return group, text

    def build_collimator(self, label, text_left=True):
        group = InteractiveGroup(label)
        outer = QGraphicsEllipseItem(-6, -6, 12, 12)
        outer.setBrush(STATUS_COLORS[UNKNOWN])
        group.addToGroup(outer)
        inner = QGraphicsEllipseItem(-3, -3, 6, 6)
        inner.setBrush(STATUS_COLORS[UNKNOWN])
        group.addToGroup(inner)
        text = QGraphicsSimpleTextItem(" " * 14)
        font = QFont("sans", 24)
        font.setStyleHint(QFont.StyleHint.Monospace)
        text.setFont(font)
        group.addToGroup(text)
        title = QGraphicsSimpleTextItem(label)
        title.setFont(QFont("sans", 26, QFont.Weight.Bold))
        # background box for text
        if text_left:
            title.setPos(
                -title.boundingRect().width() - 20, -title.boundingRect().height() / 2
            )
            text.setPos(
                -text.boundingRect().width() - title.boundingRect().width() - 30,
                -title.boundingRect().height() / 2,
            )
        else:
            title.setPos(20, -title.boundingRect().height() / 2)
            text.setPos(
                title.boundingRect().width() + 35, -title.boundingRect().height() / 2
            )
        group.addToGroup(title)
        return group, text

    def build_collimator_diagonal(self, label, text_left=True, point_down=True):
        group = InteractiveGroup(label)
        outer = QGraphicsRectItem(-6, -6, 12, 24)
        outer.setBrush(STATUS_COLORS[UNKNOWN])
        group.addToGroup(outer)
        if point_down:
            inner = QGraphicsRectItem(-3, -21 - 14, 6, 14)
        else:
            inner = QGraphicsRectItem(-3, 21, 6, 14)
        inner.setBrush(STATUS_COLORS[UNKNOWN])
        group.addToGroup(inner)
        text = QGraphicsSimpleTextItem(" " * 14)
        font = QFont("sans", 24)
        font.setStyleHint(QFont.StyleHint.Monospace)
        text.setFont(font)
        group.addToGroup(text)
        title = QGraphicsSimpleTextItem(label)
        title.setFont(QFont("sans", 26, QFont.Weight.Bold))
        if text_left:
            title.setPos(
                -title.boundingRect().width() - 20, -title.boundingRect().height() / 2
            )
            text.setPos(
                -text.boundingRect().width() - title.boundingRect().width() - 30,
                -title.boundingRect().height() / 2,
            )
        else:
            title.setPos(20, -title.boundingRect().height() / 2)
            text.setPos(
                title.boundingRect().width() + 35, -title.boundingRect().height() / 2
            )
        group.addToGroup(title)
        return group, text

    def _draw_mirrors(self):
        if self.selene != 2:
            zpre = 1
        else:
            zpre = -1
        for group in range(15):
            center_x = 265 + group * 480
            xellipse = (group - 8) * 480
            x_start = int(center_x - 240)
            x_end = int(center_x + 240)
            z_start = int(158 * np.sqrt(6000**2 - (xellipse - 240) ** 2) / 6000)
            z_end = int(158 * np.sqrt(6000**2 - (xellipse + 240) ** 2) / 6000)
            qt_polygon = QPolygonF()
            for px, py in [
                (x_start, zpre * z_start),
                (x_end, zpre * z_end),
                (x_end, zpre * (z_end + 40)),
                (x_start, zpre * (z_start + 40)),
                (x_start, zpre * z_start),
            ]:
                qt_polygon.append(QPointF(px, py))
            self.mirrors_H[group] = self.addPolygon(
                qt_polygon, brush=QColor(255, 255, 255, 220)
            )

            for px, py in [
                (x_start, zpre * z_start),
                (x_end, zpre * z_end),
                (x_end, zpre * 20),
                (x_start, zpre * 20),
                (x_start, zpre * z_start),
            ]:
                qt_polygon.append(QPointF(px, py))
            self.mirrors_V[group] = self.addPolygon(
                qt_polygon, brush=QColor(255, 255, 255, 200)
            )
            if self.selene == 2:
                text = self.addText("E02-06-%02i-VU" % (group + 1))
                textH = self.addText("E02-06-%02i-HU" % (group + 1))
            else:
                text = self.addText("E02-02-%02i-VD" % (group + 1))
                textH = self.addText("E02-02-%02i-HD" % (group + 1))
            text.setFont(QFont("sans", 30))
            text.setPos(center_x - text.boundingRect().width() / 2, zpre * 80 - 15)
            text.setDefaultTextColor(QColor(160, 160, 160))
            textH.setFont(QFont("sans", 30))
            textH.setPos(
                center_x - text.boundingRect().width() / 2,
                zpre * (max(z_start, z_end) + 10) - text.boundingRect().height() / 2,
            )
            textH.setDefaultTextColor(QColor(160, 160, 160))

    def _draw_cart(self):
        self.cart = TransmittingGroup()
        self.cart.setZValue(10.0)
        self.addItem(self.cart)

        for CHi, pos, diagonal in self.channels:
            if diagonal:
                group, value = self.build_collimator_diagonal(CHi, pos[0] < 0)
            else:
                group, value = self.build_collimator(CHi, pos[0] < 0)
            group.setParentItem(self.cart)
            group.setPos(pos[0], -pos[1])
            self.collimators[CHi] = (group, value)

        frame = QGraphicsRectItem(-135, -300, 270, 600)
        frame.setZValue(-1.0)
        frame.setBrush(QColor(128, 128, 128, 128))
        frame.setParentItem(self.cart)
        self.cart.setPos(350.0, 0.0)

    def on_client_connected(self):
        state = self.client.ask("getstatus")
        if not state:
            return
        devlist = [ci[0] for ci in self.channels] + self.positions + ["mpos"]

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

    def on_client_cache(self, data):
        (time, key, op, value) = data
        if "/" not in key:
            return
        ldevname, subkey = key.rsplit("/", 1)

        if ldevname in self.collimators:
            if subkey == "status":
                value = cache_load(value)
                for item in self.collimators[ldevname][0].childItems():
                    if hasattr(item, "setBrush"):
                        item.setBrush(STATUS_COLORS[value[0]])
            if subkey == "value":
                value = cache_load(value)
                text = self.collimators[ldevname][1]
                if text.x() < 0:
                    text.setText("%12.3f" % value)
                else:
                    text.setText("%.3f" % value)
                if ldevname == self._currentSelection:
                    self.parent().lblSeleneSelection.setText(f"{ldevname}: {value}")
        elif ldevname == self.cart_position and subkey == "value":
            value = cache_load(value) + self.offsetx
            self.cart.setPos(value + 150, 0)
            self.collimator_lines[0].setLine(value + 300, -220, 7210, -220)
            self.collimator_lines[1].setLine(value + 300, 220, 7210, 220)

    def childSelected(self, name, control):
        self._currentSelection = name
        self.on_client_connected()

    def childActivated(self, name, control):
        pass
