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
#   Kenan Muric <kenan.muric@ess.eu>
#
# *****************************************************************************


from nicos.guisupport.qt import QValidator
from nicos_ess.utilities.validators import DoubleValidator

double_validator = DoubleValidator(2, 100, 4)


def test_validate_returns_intermediate_if_empty_string():
    stat, _, _ = double_validator.validate("", 0)
    assert stat == QValidator.Intermediate


def test_validate_returns_acceptable_if_string_is_valid_float():
    stat, _, _ = double_validator.validate("50.5555", 0)
    assert stat == QValidator.Acceptable


def test_validate_returns_invalid_if_float_has_too_many_decimals():
    stat, _, _ = double_validator.validate("50.55555", 0)
    assert stat == QValidator.Invalid


def test_validate_returns_invalid_if_string_with_dots_not_float():
    stat, _, _ = double_validator.validate("12.34.55.2", 0)
    assert stat == QValidator.Invalid


def test_validate_returns_invalid_if_float_value_lower_than_min_val():
    stat, _, _ = double_validator.validate("1.5", 0)
    assert stat == QValidator.Invalid


def test_validate_returns_invalid_if_float_value_higher_than_max_val():
    stat, _, _ = double_validator.validate("105.5", 0)
    assert stat == QValidator.Invalid


def test_validate_returns_invalid_if_integer_value_lower_than_min_val():
    stat, _, _ = double_validator.validate("0", 0)
    assert stat == QValidator.Invalid


def test_validate_returns_invalid_if_integer_value_higher_than_max_val():
    stat, _, _ = double_validator.validate("105", 0)
    assert stat == QValidator.Invalid


def test_validate_returns_invalid_if_alphabetic_input():
    stat, _, _ = double_validator.validate("invalid", 0)
    assert stat == QValidator.Invalid


def test_validate_returns_acceptable_valid_integer():
    stat, _, _ = double_validator.validate("10", 0)
    assert stat == QValidator.Acceptable
