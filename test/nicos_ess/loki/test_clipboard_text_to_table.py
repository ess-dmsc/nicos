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
#   Matt Clarke <matt.clarke@ess.eu>
#
# *****************************************************************************

from nicos_ess.utilities.table_utils import extract_table_from_clipboard_text


def test_one_empty_cell():
    clipboard_data = ''
    assert extract_table_from_clipboard_text(clipboard_data) == [['']]


def test_one_non_empty_cell():
    clipboard_data = 'A'
    assert extract_table_from_clipboard_text(clipboard_data) == [['A']]


def test_empty_row():
    clipboard_data = '\t\t'
    assert extract_table_from_clipboard_text(clipboard_data) == [['', '', '']]


def test_non_empty_row():
    clipboard_data = 'A\tB\tC'

    result = extract_table_from_clipboard_text(clipboard_data)

    assert result == [['A', 'B', 'C']]


def test_empty_column():
    clipboard_data = '\n'
    assert extract_table_from_clipboard_text(clipboard_data) == [[''],
                                                                 ['']]


def test_non_empty_column():
    clipboard_data = 'A\nB'
    assert extract_table_from_clipboard_text(clipboard_data) == [['A'],
                                                                 ['B']]


def test_multiple_empty_cells():
    clipboard_data = '\t\n\t'
    assert extract_table_from_clipboard_text(clipboard_data) == [['', ''],
                                                                 ['', '']]


def test_multiple_non_empty_cells():
    clipboard_data = 'A1\tB1\nA2\tB2'
    assert extract_table_from_clipboard_text(clipboard_data) == [['A1', 'B1'],
                                                                 ['A2', 'B2']]


def test_multiple_non_empty_cells_with_excel_encoding():
    # Excel uses \r\n as the line separator
    clipboard_data = 'A1\tB1\r\nA2\tB2'
    assert extract_table_from_clipboard_text(clipboard_data) == [['A1', 'B1'],
                                                                 ['A2', 'B2']]


def test_mix_of_non_empty_cells_and_empty_cells():
    clipboard_data = '\tB1\nA2\t'
    assert extract_table_from_clipboard_text(clipboard_data) == [['', 'B1'],
                                                                 ['A2', '']]


def test_non_empty_cells_surrounded_by_empty_cells():
    clipboard_data = '\t\t\t\n\tB2\tC2\t\n\tB3\tC3\t\r\n\t\t\t'

    result = extract_table_from_clipboard_text(clipboard_data)

    assert result == [['', '', '', ''],
                     ['', 'B2', 'C2', ''],
                     ['', 'B3', 'C3', ''],
                     ['', '', '', '']]
