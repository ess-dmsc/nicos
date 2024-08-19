import re


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
