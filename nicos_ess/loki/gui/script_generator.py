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

"""LoKI Script Generator."""

from enum import Enum


class TransOrder(Enum):
    TRANSFIRST = 0
    SANSFIRST = 1
    TRANSTHENSANS = 2
    SANSTHENTRANS = 3
    SIMULTANEOUS = 4


class Steps(Enum):
    FIRST = 0
    LAST = 1


def _get_position(value):
    return f'set_position({value})'


def _get_sample(name, thickness):
    return f'set_sample("{name}", {thickness})'


def _get_temperature(temperature):
    if not temperature:
        return ''
    return f'set_temperature({temperature})\n'


def _get_command(command):
    if not command:
        return ''
    return f'{command}\n'


def _get_comment_line(name):
    return f'# Sample = {name}\n'


def _add_commands_to_template(row_template, row_values):
    return (
        f"{_get_comment_line(row_values['sample'])}"
        f"{_get_command(row_values.get('pre-command'))}"
        f"{row_template}"
        f"{_get_command(row_values.get('post-command'))}"
    )


def _do_trans(row_values, trans_duration_type):
    template = (
        f"{_get_sample(row_values['sample'], row_values['thickness'])}\n"
        f"{_get_position(row_values['position'])}\n"
        f"{_get_temperature(row_values.get('temperature'))}"
        f"do_trans({row_values['trans_duration']}, '{trans_duration_type}')\n"
    )
    return template


def _do_sans(row_values, sans_duration_type):
    template = (
        f"{_get_sample(row_values['sample'], row_values['thickness'])}\n"
        f"{_get_position(row_values['position'])}\n"
        f"{_get_temperature(row_values.get('temperature'))}"
        f"do_sans({row_values['sans_duration']}, '{sans_duration_type}')\n"
    )
    return template


def _do_simultaneous(row_values, sans_duration_type):
    template = (
        f"{_get_sample(row_values['sample'], row_values['thickness'])}\n"
        f"{_get_position(row_values['position'])}\n"
        f"{_get_temperature(row_values.get('temperature'))}"
        f"do_sans_simultaneous({row_values['sans_duration']}, "
        f"'{sans_duration_type}')\n"
    )
    return template


class TransOrderBase:
    def generate_script(self, labeled_data, trans_duration_type,
                        sans_duration_type, trans_times, sans_times):
        template = ''
        for num_time in range(max(trans_times, sans_times)):
            for step in (Steps.FIRST, Steps.LAST):
                for row_values in labeled_data:
                    row_template = self.generate_row_template(
                        row_values,
                        step,
                        num_time,
                        trans_duration_type,
                        sans_duration_type,
                        trans_times,
                        sans_times)

                    if row_template:
                        template += _add_commands_to_template(
                            row_template, row_values)
                        template += '\n'
        return template

    def generate_row_template(
        self, row_values, step, num_time,
        trans_duration_type, sans_duration_type,
        trans_times, sans_times):

        pass


class TransFirst(TransOrderBase):
    def generate_row_template(
        self, row_values, step, num_time,
        trans_duration_type, sans_duration_type,
        trans_times, sans_times):

        row_template = ''
        if step == Steps.FIRST:
            if num_time < trans_times:
                row_template = _do_trans(row_values, trans_duration_type)
        else:
            if num_time < sans_times:
                row_template = _do_sans(row_values, sans_duration_type)
        return row_template


class SansFirst(TransOrderBase):
    def generate_row_template(
        self, row_values, step, num_time,
        trans_duration_type, sans_duration_type,
        trans_times, sans_times):

        row_template = ''
        if step == Steps.FIRST:
            if num_time < sans_times:
                row_template = _do_sans(row_values, sans_duration_type)
        else:
            if num_time < trans_times:
                row_template = _do_trans(row_values, trans_duration_type)
        return row_template


class TransThenSans(TransOrderBase):
    def generate_row_template(
        self, row_values, step, num_time,
        trans_duration_type, sans_duration_type,
        trans_times, sans_times):

        row_template = ''
        if step == Steps.FIRST:
            if num_time < trans_times:
                row_template += _do_trans(row_values, trans_duration_type)
            if num_time < sans_times:
                row_template += _do_sans(row_values, sans_duration_type)

        return row_template


class SansThenTrans(TransOrderBase):
    def generate_row_template(
        self, row_values, step, num_time,
        trans_duration_type, sans_duration_type,
        trans_times, sans_times):

        row_template = ''
        if step == Steps.FIRST:
            if num_time < sans_times:
                row_template += _do_sans(row_values, sans_duration_type)
            if num_time < trans_times:
                row_template += _do_trans(row_values, trans_duration_type)

        return row_template


class Simultaneous(TransOrderBase):
    def generate_row_template(
        self, row_values, step, num_time,
        trans_duration_type, sans_duration_type,
        trans_times, sans_times):

        row_template = ''
        if step == Steps.FIRST:
            if num_time < sans_times:
                row_template += _do_simultaneous(row_values, sans_duration_type)

        return row_template


class ScriptGenerator:
    @classmethod
    def from_trans_order(cls, trans_order):
        classes_by_trans_order = {
            TransOrder.TRANSFIRST: TransFirst,
            TransOrder.SANSFIRST: SansFirst,
            TransOrder.TRANSTHENSANS: TransThenSans,
            TransOrder.SANSTHENTRANS: SansThenTrans,
            TransOrder.SIMULTANEOUS: Simultaneous
        }
        if trans_order in classes_by_trans_order:
            return classes_by_trans_order[trans_order]()
        else:
            raise NotImplementedError(
                f'Unspecified trans order {trans_order.name}')
