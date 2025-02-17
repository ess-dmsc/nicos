"""Helpers for working with tables."""

import re

from PyQt5.QtCore import Qt
from PyQt5.QtWidgets import QApplication


def extract_table_from_clipboard_text(text):
    """
    Extracts 2-D tabular data from clipboard text.

    When sent to the clipboard, tabular data from Excel, etc. is represented as
    a text string with tabs for columns and newlines for rows.

    :param text: The clipboard text
    :return: tabular data
    """
    # Uses re.split because "A\n" represents two vertical cells one
    # containing "A" and one being empty.
    # str.splitlines will lose the empty cell but re.split won't
    return [row.split("\t") for row in re.split("\r?\n", text)]


def convert_table_to_clipboard_text(table_data):
    """
    Converts 2-D tabular data to clipboard text.

    :param table_data: 2D tabular data
    :return: clipboard text
    """
    return "\n".join(["\t".join(row) for row in table_data])


class Clipboard:
    def __init__(self):
        self.clipboard = QApplication.instance().clipboard()

    def set_text(self, text):
        self.clipboard.setText(text)

    def has_text(self):
        return self.clipboard.mimeData().hasText()

    def text(self):
        return self.clipboard.text()


class TableHelper:
    def __init__(self, table_view, model, clipboard):
        self.table_view = table_view
        self.model = model
        self.clipboard = clipboard

    def _select_table_data(self):
        curr_row = -1
        row_data = []
        selected_data = []
        for index in self.table_view.selectedIndexes():
            row = index.row()
            column = index.column()
            if row != curr_row and row_data:
                selected_data.append(row_data)
                row_data = []
            curr_row = row
            row_data.append(str(self.model.table_data[row][column]))

        if row_data:
            selected_data.append(row_data)
        return selected_data

    def copy_selected_to_clipboard(self):
        selected_data = self._select_table_data()
        clipboard_text = convert_table_to_clipboard_text(selected_data)
        self.clipboard.set_text(clipboard_text)

    def clear_selected(self):
        for index in self.table_view.selectedIndexes():
            self.model.setData(index, "", Qt.ItemDataRole.EditRole)

    def cut_selected_to_clipboard(self):
        self.copy_selected_to_clipboard()
        self.clear_selected()

    def paste_from_clipboard(self, expand=True):
        if not self.clipboard.has_text() or not self.table_view.selectedIndexes():
            return

        clipboard_text = self.clipboard.text()
        copied_table = extract_table_from_clipboard_text(clipboard_text)

        if len(copied_table) == 1 and len(copied_table[0]) == 1:
            # Only one value, so put it in all selected cells
            for index in self.table_view.selectedIndexes():
                self.model.setData(index, copied_table[0][0], Qt.ItemDataRole.EditRole)
            return

        # Copied data is tabular so insert at top-left most position
        top_left = self.table_view.selectedIndexes()[0]
        column_indexes = [
            i
            for i, _ in enumerate(self.model._headings)
            if not self.table_view.isColumnHidden(i) and i >= top_left.column()
        ]
        for row_index, row_data in enumerate(copied_table):
            current_row = top_left.row() + row_index
            if current_row == self.model.num_entries:
                if not expand:
                    break
                self.model.insert_row(current_row)

            for col_index, value in zip(column_indexes, row_data):
                self.model.setData(
                    self.model.index(current_row, col_index),
                    value,
                    Qt.ItemDataRole.EditRole,
                )
