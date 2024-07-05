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
#   Ebad Kamil <Ebad.Kamil@ess.eu>
#   Matt Clarke <matt.clarke@ess.eu>
#
# *****************************************************************************
"""Useful delegates for tables."""

from nicos.guisupport.qt import (
    QAbstractSpinBox,
    QComboBox,
    QDoubleSpinBox,
    QItemDelegate,
    Qt,
    QStyledItemDelegate,
    QStyleOptionButton,
    QStyle,
    QApplication,
    QPoint,
    QRect,
)


class LimitsDelegate(QItemDelegate):
    def __init__(self, limits=(0, 0), precision=3):
        QItemDelegate.__init__(self)
        self.limits = limits
        self.precision = precision

    def createEditor(self, parent, option, index):
        return self._create_widget(parent)

    def _create_widget(self, parent):
        spinbox = QDoubleSpinBox(parent)
        spinbox.setButtonSymbols(QAbstractSpinBox.ButtonSymbols.NoButtons)
        spinbox.setMinimum(self.limits[0])
        spinbox.setMaximum(self.limits[1])
        spinbox.setDecimals(self.precision)
        return spinbox


class ReadOnlyDelegate(QItemDelegate):
    def createEditor(self, parent, option, index):
        return None


class ComboBoxDelegate(QItemDelegate):
    def __init__(self):
        QItemDelegate.__init__(self)
        self.items = []

    def createEditor(self, parent, option, index):
        editor = QComboBox(parent)
        editor.addItems(self.items)
        return editor


class CheckboxDelegate(QStyledItemDelegate):
    def __init__(self, parent=None):
        super(CheckboxDelegate, self).__init__(parent)
        self.model = None

    def paint(self, painter, option, index):
        if self.model is None:
            self.model = index.model()

        checked = self.model.data(index, Qt.ItemDataRole.DisplayRole)
        opts = QStyleOptionButton()

        if index.flags() & Qt.ItemFlag.ItemIsEditable:
            opts.state |= QStyle.StateFlag.State_Enabled
        else:
            opts.state |= QStyle.StateFlag.State_ReadOnly

        if checked:
            opts.state |= QStyle.StateFlag.State_On
        else:
            opts.state |= QStyle.StateFlag.State_Off

        opts.rect = self.getCheckBoxRect(option)
        QApplication.style().drawControl(
            QStyle.ControlElement.CE_CheckBox, opts, painter
        )

    def editorEvent(self, event, model, option, index):
        self.model = model
        if not (index.flags() & Qt.ItemFlag.ItemIsEditable):
            return False

        if (
            event.type() == event.Type.MouseButtonPress
            or event.type() == event.Type.MouseButtonRelease
        ):
            if event.button() != Qt.MouseButton.LeftButton:
                return False

        if event.type() == event.Type.MouseButtonDblClick:
            return False

        if event.type() == event.Type.MouseButtonRelease:
            if self.getCheckBoxRect(option).contains(event.pos()):
                checked = self.model.data(index, Qt.ItemDataRole.DisplayRole)
                checked = not checked
                self.model.setData(index, checked, Qt.ItemDataRole.EditRole)
                return True
        return False

    def getCheckBoxRect(self, option):
        opts = QStyleOptionButton()
        checkBoxRect = QApplication.style().subElementRect(
            QStyle.SubElement.SE_CheckBoxIndicator, opts, None
        )
        x = option.rect.x()
        y = option.rect.y()
        w = option.rect.width()
        h = option.rect.height()
        checkBoxTopLeftCorner = QPoint(
            x + w / 2 - checkBoxRect.width() / 2, y + h / 2 - checkBoxRect.height() / 2
        )
        return QRect(checkBoxTopLeftCorner, checkBoxRect.size())
