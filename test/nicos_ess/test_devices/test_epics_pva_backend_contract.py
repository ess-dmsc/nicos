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
#   NICOS contributors
#
# *****************************************************************************

"""Contract tests for the EPICS PVA backend test double.

These tests keep ``FakeEpicsBackend`` aligned with the production wrapper
surface used by ``nicos_ess.devices.epics.pva.epics_devices``.
"""

import ast
import inspect
from pathlib import Path

import nicos_ess.devices.epics.pva.epics_devices as epics_devices
import pytest

from nicos.core import status
from test.nicos_ess.test_devices.doubles.epics_pva_backend import (
    FakeEpicsBackend,
    patch_create_wrapper,
)

WRAPPER_CLASS_FILES = {
    "P4pWrapper": Path("nicos/devices/epics/pva/p4p.py"),
    "CaprotoWrapper": Path("nicos/devices/epics/pva/caproto.py"),
}

COMMON_WRAPPER_METHODS = [
    "connect_pv",
    "get_pv_value",
    "put_pv_value",
    "get_units",
    "get_limits",
    "get_alarm_status",
    "get_value_choices",
    "subscribe",
]


def _repo_root():
    return Path(__file__).resolve().parents[3]


def _get_class_node(module_path, class_name):
    tree = ast.parse(module_path.read_text(encoding="utf-8"), filename=str(module_path))
    for node in tree.body:
        if isinstance(node, ast.ClassDef) and node.name == class_name:
            return node
    raise AssertionError(f"Class {class_name!r} not found in {module_path}")


def _get_method_node(class_node, method_name):
    for node in class_node.body:
        if isinstance(node, ast.FunctionDef) and node.name == method_name:
            return node
    raise AssertionError(f"Method {method_name!r} not found in class {class_node.name!r}")


def _signature_spec_from_ast(method_node):
    args = method_node.args
    positional = list(args.posonlyargs) + list(args.args)
    defaults = [None] * (len(positional) - len(args.defaults)) + list(args.defaults)

    return {
        "positional": tuple(
            (arg.arg, default is not None)
            for arg, default in zip(positional, defaults)
        ),
        "kwonly": tuple(
            (arg.arg, default is not None)
            for arg, default in zip(args.kwonlyargs, args.kw_defaults)
        ),
        "vararg": args.vararg.arg if args.vararg else None,
        "kwarg": args.kwarg.arg if args.kwarg else None,
    }


def _signature_spec_from_callable(func):
    sig = inspect.signature(func)
    positional = []
    kwonly = []
    vararg = None
    kwarg = None

    for param in sig.parameters.values():
        has_default = param.default is not inspect.Signature.empty
        if param.kind in (
            inspect.Parameter.POSITIONAL_ONLY,
            inspect.Parameter.POSITIONAL_OR_KEYWORD,
        ):
            positional.append((param.name, has_default))
        elif param.kind == inspect.Parameter.KEYWORD_ONLY:
            kwonly.append((param.name, has_default))
        elif param.kind == inspect.Parameter.VAR_POSITIONAL:
            vararg = param.name
        elif param.kind == inspect.Parameter.VAR_KEYWORD:
            kwarg = param.name

    return {
        "positional": tuple(positional),
        "kwonly": tuple(kwonly),
        "vararg": vararg,
        "kwarg": kwarg,
    }


def _wrapper_specs_from_source():
    specs = {}
    for class_name, relative_path in WRAPPER_CLASS_FILES.items():
        class_node = _get_class_node(_repo_root() / relative_path, class_name)
        method_specs = {}
        for method_name in COMMON_WRAPPER_METHODS:
            method_specs[method_name] = _signature_spec_from_ast(
                _get_method_node(class_node, method_name)
            )
        specs[class_name] = method_specs
    return specs


WRAPPER_SPECS = _wrapper_specs_from_source()


@pytest.mark.parametrize("method_name", COMMON_WRAPPER_METHODS)
def test_pva_wrappers_share_common_method_contract(method_name):
    # Both production wrappers should expose the same API surface.
    assert WRAPPER_SPECS["P4pWrapper"][method_name] == WRAPPER_SPECS["CaprotoWrapper"][
        method_name
    ]


@pytest.mark.parametrize("method_name", COMMON_WRAPPER_METHODS)
def test_fake_epics_backend_matches_wrapper_method_contract(method_name):
    # The fake backend must stay drop-in compatible for device tests.
    fake_spec = _signature_spec_from_callable(getattr(FakeEpicsBackend, method_name))
    wrapper_spec = WRAPPER_SPECS["P4pWrapper"][method_name]
    assert fake_spec == wrapper_spec


def test_patch_create_wrapper_injects_backend_for_pva_and_ca(monkeypatch):
    # Setup
    backend = patch_create_wrapper(monkeypatch, epics_devices)

    # Act + Assert
    assert epics_devices.create_wrapper(timeout=1.0, use_pva=True) is backend
    assert epics_devices.create_wrapper(timeout=1.0, use_pva=False) is backend


def test_fake_backend_defaults_follow_wrapper_style_for_units_and_limits():
    # Setup
    backend = FakeEpicsBackend()

    # Act + Assert
    assert backend.get_units("PV:UNKNOWN", default="Hz") == "Hz"
    assert backend.get_limits("PV:UNKNOWN", default_low=-5, default_high=15) == (-5, 15)


def test_fake_backend_subscription_callback_shape_matches_wrapper_contract():
    # Setup
    backend = FakeEpicsBackend()
    observed_changes = []
    observed_connections = []

    def on_change(pvname, pvparam, value, units, limits, severity, message):
        observed_changes.append((pvname, pvparam, value, units, limits, severity, message))

    def on_connection(pvname, pvparam, is_connected):
        observed_connections.append((pvname, pvparam, is_connected))

    # Act
    token = backend.subscribe(
        "SIM:READ.RBV",
        "value",
        on_change,
        on_connection,
        as_string=True,
    )
    backend.emit_connection("SIM:READ.RBV", True)
    backend.emit_update(
        "SIM:READ.RBV",
        value=2.5,
        units="A",
        limits=(0.0, 10.0),
        severity=status.WARN,
        message="minor alarm",
    )

    # Assert
    assert token == ("SIM:READ.RBV", "value", on_change, on_connection)
    assert observed_connections == [("SIM:READ.RBV", "value", True)]
    assert observed_changes == [
        (
            "SIM:READ.RBV",
            "value",
            2.5,
            "A",
            (0.0, 10.0),
            status.WARN,
            "minor alarm",
        )
    ]


def test_fake_backend_put_records_wait_flag_for_future_wait_paths():
    # Setup
    backend = FakeEpicsBackend()

    # Act
    backend.put_pv_value("SIM:WRITE.VAL", 14.0)
    backend.put_pv_value("SIM:WRITE.VAL", 18.0, wait=True)

    # Assert
    assert backend.put_calls == [
        ("SIM:WRITE.VAL", 14.0, False),
        ("SIM:WRITE.VAL", 18.0, True),
    ]
