from PyQt5.QtCore import Qt, QModelIndex

from tablemodel import TableModel


class SampleTableModel(TableModel):
    def __init__(self, columns, num_rows=2):
        TableModel.__init__(self, headings=columns, mappings=None)
        # self._default_num_rows = num_rows
        self.raw_data = [{} for _ in range(num_rows)]
        # # self._table_data = self._empty_table(len(columns), num_rows)
        #
        # # self.positions = [range(1, num_rows+1)]
        # # self.columns = columns
        # print(self.raw_data)
        # print(self.table_data)

    def setData(self, index, value, role):
        if role != Qt.ItemDataRole.EditRole:
            return False
        row, column = self._get_row_and_column(index)
        value = value.strip()
        self._table_data[row][column] = value
        self._raw_data[row][self._headings[column]] = value
        self._emit_update()
        return True

    def headerData(self, section, orientation, role):
        if (
            role == Qt.ItemDataRole.DisplayRole
            and orientation == Qt.Orientation.Horizontal
        ):
            return self._headings[section]
        if (
            role == Qt.ItemDataRole.DisplayRole
            and orientation == Qt.Orientation.Vertical
        ):
            return section + 1

    def setHeaderData(
        self, section, orientation, value, role=Qt.ItemDataRole.DisplayRole
    ):
        if (
            role == Qt.ItemDataRole.DisplayRole
            and orientation == Qt.Orientation.Horizontal
        ):
            self._headings[section] = value
            self.headerDataChanged.emit(orientation, section, section)
        return True

    @property
    def column_headers(self):
        return self._headings

    def add_column_header(self, name, col_index):
        self.column_headers.insert(col_index, name)

    def delete_column_header(self, col_index):
        del self.column_headers[col_index]

    def insert_column(self, col_index, name):
        self.beginInsertColumns(QModelIndex(), col_index, col_index)
        self.add_column_header(name, col_index)

        new_raw_data = []
        for row in self.raw_data:
            new_row = {}
            for i, (key, val) in enumerate(row.items()):
                if i == col_index:
                    new_row[name] = ""
                new_row[key] = val
            new_raw_data.append(new_row)
        self.raw_data = new_raw_data

        self.endInsertColumns()
        self._emit_update()

    def delete_columns(self, col_indices):
        self.beginRemoveColumns(QModelIndex(), min(col_indices), max(col_indices))
        col_indices_reverse = sorted(list(set(col_indices)), reverse=True)
        for col_index in col_indices_reverse:
            if col_index == 0:
                continue
            self.delete_column_header(col_index)

            new_raw_data = []
            for row in self.raw_data:
                new_row = {}
                for i, (key, val) in enumerate(row.items()):
                    if i != col_index:
                        new_row[key] = val
                new_raw_data.append(new_row)
            self.raw_data = new_raw_data

        self.endRemoveColumns()
        self._emit_update()

    def rename_column(self, index, new_col_name):
        self.delete_column_header(index)
        self.add_column_header(new_col_name, index)

        new_raw_data = []
        for row in self.raw_data:
            new_row = {}
            for i, (key, val) in enumerate(row.items()):
                if i == index:
                    new_row[new_col_name] = val
                else:
                    new_row[key] = val
            new_raw_data.append(new_row)
        self.raw_data = new_raw_data
        self._emit_update()

    def clear(self):
        """Clears the data but keeps the rows."""
        self.raw_data = [{} for _ in self.raw_data]

    def _empty_table(self, columns, rows):
        return [[""] * columns for _ in range(rows)]
