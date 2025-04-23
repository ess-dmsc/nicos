from nicos_ess.gui.panels.samples_model import SampleTableModel


def create_data():
    headers = ["header1", "header2"]
    data = [
        dict(zip(headers, ["val11", "val12"])),
        dict(zip(headers, ["val21", "val22"])),
    ]
    return headers, data


class TestSampleModel:
    def test_add_row(self):
        headers, data = create_data()
        model = SampleTableModel(headers)
        model.raw_data = data
        model.insert_row(2)
        assert len(model.raw_data) == 3

    def test_remove_row(self):
        headers, data = create_data()
        model = SampleTableModel(headers)
        model.raw_data = data
        model.remove_rows([1])
        assert len(model.raw_data) == 1

    def test_copy_row(self):
        headers, data = create_data()
        model = SampleTableModel(headers)
        model.raw_data = data
        model.copy_rows([0])
        assert len(model.raw_data) == 3 and model.raw_data[0] == model.raw_data[1]

    def test_copy_rows(self):
        headers, data = create_data()
        model = SampleTableModel(headers)
        model.raw_data = data
        model.copy_rows([0, 1])
        assert (
            model.raw_data[0] == model.raw_data[2]
            and model.raw_data[1] == model.raw_data[3]
        )

    def test_add_column(self):
        headers, data = create_data()
        model = SampleTableModel(headers)
        model.raw_data = data
        new_column_name = "header3"
        model.insert_column(2, new_column_name)
        assert len(model.column_headers) == 3

    def test_remove_column(self):
        headers, data = create_data()
        model = SampleTableModel(headers)
        model.raw_data = data
        model.remove_columns([1])
        assert len(model.column_headers) == 1

    def test_rename_column(self):
        headers, data = create_data()
        model = SampleTableModel(headers)
        model.raw_data = data
        i, new_col_name = 1, "new_col_name"
        model.rename_column(i, new_col_name)
        assert model.column_headers[1] == new_col_name
