import csv


def export_table_to_csv_file(filename, data, headers=None):
    """Export 2D data to a csv text file.

    :param filename: file to save as
    :param data: 2D data list
    :param headers: list of column names
    """
    with open(filename, "w", encoding="utf-8") as file:
        export_table_to_csv_stream(file, data, headers)


def export_table_to_csv_stream(stream, data, headers=None):
    """Export 2D data to a csv stream.

    Typically, used with an open file-like object where any preceding non-csv
    data has already been written.

    :param stream: the open stream
    :param data: 2D data list
    :param headers: list of column names
    """
    writer = csv.writer(stream)
    if headers:
        writer.writerow(headers)
    writer.writerows(data)


def import_table_from_csv_file(filename):
    """Import tabular data from a csv file.

    :param filename: path to csv file
    :return: tuple of headers (empty if no headers) and rows
    """
    with open(filename, "r", encoding="utf-8") as file:
        return import_table_from_csv_stream(file)


def import_table_from_csv_stream(stream):
    """Import tabular data from a csv containing stream.

    Typically, used from an open file-like object where any preceding non-csv
    data has already been consumed.

    :param stream: the open stream
    :return: tuple of headers (empty if no headers) and rows
    """
    offset = stream.tell()
    sniffer = csv.Sniffer()
    has_header = sniffer.has_header(stream.read(2048))
    stream.seek(offset)
    rows = list(csv.reader(stream))
    if has_header:
        return rows[0], rows[1:]
    return [], rows
