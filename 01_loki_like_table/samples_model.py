from PyQt5.QtCore import Qt, QModelIndex

from tablemodel import TableModel


class SampleTableModel(TableModel):
    def __init__(self, columns, num_rows=2):
        TableModel.__init__(self, headings=list(columns.keys()), mappings=None)
        self._default_num_rows = num_rows
        self._raw_data = [{} for _ in range(num_rows)]
        self._table_data = self._empty_table(len(columns), num_rows)
        self.positions = [range(1, num_rows + 1)]
        self.columns = columns

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

    def insert_column(self, position, name):
        self.beginInsertColumns(QModelIndex(), position, position)
        self._headings.insert(position, name)

        new_columns = list(self.columns.items())
        new_columns.insert(position, (name, name))
        self.columns = dict(new_columns)

        new_raw_data = []
        for row in self._raw_data:
            new_row = {}
            for i, (key, val) in enumerate(row.items()):
                if i == position:
                    new_row[name] = ""
                new_row[key] = val
            new_raw_data.append(new_row)
        self._raw_data = new_raw_data

        new_table_data = []
        for row in self._table_data:
            row.insert(position, "")
            new_table_data.append(row)
        self._table_data = new_table_data

        self.endInsertColumns()
        self._emit_update()

    def delete_columns(self, column_indices):
        self.beginRemoveColumns(QModelIndex(), min(column_indices), max(column_indices))
        for index in sorted(column_indices, reverse=True):
            if index == 0:
                continue
            del self._headings[index]
            columns_key = list(self.columns.keys())[index]
            del self.columns[columns_key]

            new_raw_data = []
            for row in self._raw_data:
                new_row = {}
                for i, (key, val) in enumerate(row.items()):
                    if i != index:
                        new_row[key] = val
                new_raw_data.append(new_row)
            self._raw_data = new_raw_data

            new_table_data = []
            for row in self._table_data:
                del row[index]
                new_table_data.append(row)
            self._table_data = new_table_data

        self.endRemoveColumns()
        self._emit_update()

    def clear(self):
        """Clears the data but keeps the rows."""
        self._raw_data = [{} for _ in self._raw_data]
        self._table_data = self._empty_table(
            len(self.columns.keys()), len(self._raw_data)
        )
        self._emit_update()

    def _empty_table(self, columns, rows):
        return [[""] * columns for _ in range(rows)]
