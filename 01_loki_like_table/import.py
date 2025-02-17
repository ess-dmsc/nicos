from csv_utils import import_table_from_csv_file

fname = "testdata/two_samples.csv"

headers, data = import_table_from_csv_file(fname)

print(headers)
print(data)

raw_data = []
for row in data:
    # Clear sample info as it will be auto-populated
    # row[1] = ""
    raw_data.append(dict(zip(headers, row)))
