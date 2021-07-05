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
#   AÜC Hardal <umit.hardal@ess.eu>
#
# *****************************************************************************

import time
from contextlib import contextmanager
from typing import List


def wait_until_true(conditions, max_call_count=61, sleep_duration=1):
    """
    A generator that takes one or more boolean valued callables to
    check against. Yields when all the conditions are true, otherwise times out.
    Here the maximum call count represents how many times a call should be made
    for the truth values of the given conditions. By default, the generator will
    time out in about 60 seconds.

    Note that with the current implementation, the conditions are evaluated
    serially. A parallel implementation can be done, if needed.

    This generator should not be confused with a proper context manager which
    can only yield once. Thus decorating this generator as a context
    manager shall fail.
    """
    if not isinstance(conditions, List):
        raise TypeError('The argument should be a list.')
    for condition in conditions:
        if not isinstance(condition, bool):
            raise TypeError('The elements should be boolean valued.')
    if not conditions:
        raise ValueError('There should be at least one condition to be'
                         'satisfied.')

    call_count = 1

    for condition in conditions:
        while not condition:
            if call_count == max_call_count:
                raise ValueError('Timeout: An unknown exception occurred.')
            time.sleep(sleep_duration)
            call_count += 1
    yield


@contextmanager
def wait_before(wait_time=1):
    """
    Sleep for a given time before yielding.
    """
    time.sleep(wait_time)
    yield


@contextmanager
def wait_after(wait_time=1):
    """
    Sleep for a given time after yielding.
    """
    yield
    time.sleep(wait_time)
