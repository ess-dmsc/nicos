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
#
#   Ebad Kamil <Ebad.Kamil@ess.eu>
#   Matt Clarke <matt.clarke@ess.eu>
#
# *****************************************************************************

"""Fundamental Functionalities of a Table View Widget."""

from nicos.clients.flowui.panels import get_icon
from nicos.guisupport.qt import QAction, QApplication, QCursor, QKeySequence, \
    QMenu, QShortcut, Qt

from nicos_ess.utilities.table_utils import convert_table_to_clipboard_text, \
    extract_table_from_clipboard_text


class LokiTableViewBase:
    def __init__(self):
        self.base_view = None
        self.base_model = None
        self.optional_columns = {}
        self.columns_in_order = []

    def set_base_view(self, view, model,
                      optional_columns, all_columns_in_order):
        self.base_view = view
        self.base_model = model
        self.optional_columns = optional_columns
        self.columns_in_order = all_columns_in_order

    def _init_right_click_context_menu(self):
        self.base_view.setContextMenuPolicy(Qt.CustomContextMenu)
        self.base_view.customContextMenuRequested.connect(
            self._show_context_menu)

    def _show_context_menu(self):
        menu = QMenu()

        copy_action = QAction("Copy", self)
        copy_action.triggered.connect(self._handle_copy_cells)
        copy_action.setIcon(get_icon("file_copy-24px.svg"))
        menu.addAction(copy_action)

        cut_action = QAction("Cut", self)
        cut_action.triggered.connect(self._handle_cut_cells)
        cut_action.setIcon(get_icon("cut_24px.svg"))
        menu.addAction(cut_action)

        paste_action = QAction("Paste", self)
        paste_action.triggered.connect(self._handle_table_paste)
        paste_action.setIcon(get_icon("paste_24px.svg"))
        menu.addAction(paste_action)

        delete_action = QAction("Delete", self)
        delete_action.triggered.connect(self._delete_rows)
        delete_action.setIcon(get_icon("remove-24px.svg"))
        menu.addAction(delete_action)

        menu.exec_(QCursor.pos())

    def _create_keyboard_shortcuts(self):
        for key, to_call in [
            (QKeySequence.Paste, self._handle_table_paste),
            (QKeySequence.Cut, self._handle_cut_cells),
            (QKeySequence.Copy, self._handle_copy_cells),
            ("Ctrl+Backspace", self._delete_rows),
        ]:
            self._create_shortcut_key(key, to_call)

    def _create_shortcut_key(self, shortcut_keys, to_call):
        shortcut = QShortcut(shortcut_keys, self.base_view)
        shortcut.activated.connect(to_call)
        shortcut.setContext(Qt.WidgetShortcut)

    def is_data_in_hidden_columns(self):
        optional_indices = [index for index, element in
                            enumerate(self.columns_in_order)
                            if element in self.optional_columns.keys()]
        # Transform table_data to allow easy access to columns like data[0]
        data = list(zip(*self.base_model.table_data))
        return any(
            (any(data[column])
             for column in optional_indices
             if self.base_view.isColumnHidden(column)))

    def _extract_headers_from_table(self):
        headers = [column
                   for idx, column in enumerate(self.columns_in_order)
                   if not self.base_view.isColumnHidden(idx)]
        return headers

    def _extract_data_from_table(self):
        table_data = self.base_model.table_data
        # Remove hidden columns from data
        data = []
        for row, row_data in enumerate(table_data):
            relevant_column = []
            for column, column_data in enumerate(row_data):
                if not self.base_view.isColumnHidden(column):
                    relevant_column.append(column_data)
            data.append(relevant_column)
        # Remove the trailing empty rows
        for row, row_data in reversed(list(enumerate(data))):
            if any(row_data):
                break
            else:
                data.pop(row)
        return data

    def _delete_rows(self):
        rows_to_remove = set()
        for index in self.base_view.selectedIndexes():
            rows_to_remove.add(index.row())
        rows_to_remove = list(rows_to_remove)
        self.base_view.model().removeRows(rows_to_remove)

    def _insert_row_above(self):
        lowest, _ = self._get_selected_rows_limits()
        if lowest is not None:
            self.base_view.model().insertRow(lowest)
        elif self.base_model.num_rows == 0:
            self.base_view.model().insertRow(0)

    def _insert_row_below(self):
        _, highest = self._get_selected_rows_limits()
        if highest is not None:
            self.base_view.model().insertRow(highest + 1)
        elif self.base_model.num_rows == 0:
            self.base_view.model().insertRow(0)

    def _get_selected_rows_limits(self):
        lowest = None
        highest = None
        for index in self.base_view.selectedIndexes():
            if lowest is None:
                lowest = index.row()
                highest = index.row()
                continue
            lowest = min(lowest, index.row())
            highest = max(highest, index.row())
        return lowest, highest

    def _handle_cut_cells(self):
        self._handle_copy_cells()
        self._handle_delete_cells()

    def _handle_delete_cells(self):
        for index in self.base_view.selectedIndexes():
            self.base_model.update_data_at_index(index.row(),
                                                 index.column(), '')

    def _handle_copy_cells(self):
        selected_data = self._extract_selected_data()
        clipboard_text = convert_table_to_clipboard_text(selected_data)
        QApplication.instance().clipboard().setText(clipboard_text)

    def _extract_selected_data(self):
        selected_indices = []
        for index in self.base_view.selectedIndexes():
            if self.base_view.isColumnHidden(index.column()):
                # Don't select hidden columns
                continue
            selected_indices.append((index.row(), index.column()))

        selected_data = self.base_model.select_data(selected_indices)
        return selected_data

    def _get_hidden_column_indices(self):
        return [idx for idx, _ in enumerate(self.columns_in_order)
                if self.base_view.isColumnHidden(idx)]

    def _get_hidden_column_names(self):
        return [name for idx, name in enumerate(self.columns_in_order)
                if self.base_view.isColumnHidden(idx)]

    def _handle_table_paste(self):
        indices = []
        for index in self.base_view.selectedIndexes():
            indices.append((index.row(), index.column()))

        if not indices:
            return
        top_left = indices[0]

        data_type = QApplication.instance().clipboard().mimeData()

        if not data_type.hasText():
            # Don't paste images etc.
            return

        clipboard_text = QApplication.instance().clipboard().text()
        copied_table = extract_table_from_clipboard_text(clipboard_text)

        if len(copied_table) == 1 and len(copied_table[0]) == 1:
            # Only one value, so put it in all selected cells
            self._do_bulk_update(copied_table[0][0])
            return

        self.base_model.update_data_from_clipboard(
            copied_table, top_left, self._get_hidden_column_indices()
        )

    def _do_bulk_update(self, value):
        for index in self.base_view.selectedIndexes():
            self.base_model.update_data_at_index(index.row(),
                                                 index.column(), value)

    def _on_optional_column_toggled(self, column_name, state):
        if state == Qt.Checked:
            self._show_column(column_name)
        else:
            self._hide_column(column_name)

    def _hide_column(self, column_name):
        column_number = self.columns_in_order.index(column_name)
        self.base_view.setColumnHidden(column_number, True)

    def _show_column(self, column_name):
        column_number = self.columns_in_order.index(column_name)
        self.base_view.setColumnHidden(column_number, False)

    def _set_column_title(self, index, title):
        self.base_model.setHeaderData(index, Qt.Horizontal, title)
