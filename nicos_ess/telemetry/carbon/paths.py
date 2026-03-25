# *****************************************************************************
# NICOS, the Networked Instrument Control System of the MLZ
# Copyright (c) 2009-2024 by the NICOS contributors (see AUTHORS)
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
#   Jonas Petersson <jonas.petersson@ess.eu>
#
# *****************************************************************************

"""Graphite-safe metric path helpers."""

from __future__ import annotations

import re

_VALID_SEGMENT_RE = re.compile(r"[^A-Za-z0-9_-]+")
_MULTI_UNDERSCORE_RE = re.compile(r"_+")


def sanitize_segment(segment: str) -> str:
    """Convert one metric path segment to a Graphite-safe token."""
    text = _VALID_SEGMENT_RE.sub("_", str(segment).strip().lower())
    text = _MULTI_UNDERSCORE_RE.sub("_", text).strip("_")
    return text or "unknown"


def sanitize_path(path: str) -> str:
    """Sanitize a dot-delimited metric path."""
    parts = [sanitize_segment(part) for part in str(path).split(".") if part]
    return ".".join(parts) if parts else "unknown"
