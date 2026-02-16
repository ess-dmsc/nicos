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

"""Harness tests for `nicos_ess.devices.mapped_controller` devices.

These tests focus on:
- attached-device wiring via NICOS `Attach` logic
- mapped target/read behavior
- selector/composer/multi-target chain integration
"""

import pytest

from nicos.core import InvalidValueError, LimitError, status

from nicos_ess.devices.mapped_controller import (
    MappedController,
    MultiTargetComposer,
    MultiTargetMapping,
    MultiTargetSelector,
)
from test.nicos_ess.test_devices.doubles.mapped_controller_devices import (
    HarnessLinearAxis,
    HarnessMoveableNoPrecision,
)


def _create_master(daemon_device_harness, devcls, /, *args, **kwargs):
    """Create devices in master mode so doStart/doStatus logic is exercised."""
    return daemon_device_harness.create_master(devcls, *args, **kwargs)


class TestMappedControllerHarness:
    """Behavior tests for `MappedController` with attached moveable devices."""

    def test_attached_device_by_name_delegates_start_read_and_status(self, daemon_device_harness):
        # Setup
        axis = _create_master(daemon_device_harness,
            HarnessLinearAxis,
            name="axis",
            abslimits=(0.0, 100.0),
            precision=0.1,
            initial_value=10.0,
        )
        controller = _create_master(daemon_device_harness,
            MappedController,
            name="mapped_ctrl",
            controlled_device="axis",
            mapping={"park": 10.0, "sample": 25.0},
        )

        # Act
        controller.start("sample")

        # Assert
        assert controller._attached_controlled_device is axis
        assert axis.read(0) == 25.0
        assert controller.read(0) == "sample"
        assert controller.status(0) == axis.status(0)

    def test_is_allowed_reports_unknown_mapping_key(self, daemon_device_harness):
        # Setup
        _create_master(daemon_device_harness,
            HarnessLinearAxis,
            name="axis",
            abslimits=(0.0, 100.0),
            precision=0.1,
            initial_value=0.0,
        )
        controller = _create_master(daemon_device_harness,
            MappedController,
            name="mapped_ctrl",
            controlled_device="axis",
            mapping={"park": 0.0},
        )

        # Act
        allowed, reason = controller.isAllowed("missing")

        # Assert
        assert allowed is False
        assert "not in mapping" in reason[0]

    def test_is_allowed_reflects_limits_of_attached_device(self, daemon_device_harness):
        # Setup
        _create_master(daemon_device_harness,
            HarnessLinearAxis,
            name="axis",
            abslimits=(0.0, 10.0),
            userlimits=(0.0, 5.0),
            precision=0.1,
            initial_value=0.0,
        )
        controller = _create_master(daemon_device_harness,
            MappedController,
            name="mapped_ctrl",
            controlled_device="axis",
            mapping={"ok": 4.0, "too_high": 8.0},
        )

        # Act
        allowed, reason = controller.isAllowed("too_high")

        # Assert
        assert allowed is False
        assert "Not allowed" in reason[0]

    def test_write_mapping_rejects_targets_outside_controlled_device_limits(
        self, daemon_device_harness
    ):
        # Setup
        _create_master(daemon_device_harness,
            HarnessLinearAxis,
            name="axis",
            abslimits=(0.0, 10.0),
            userlimits=(0.0, 5.0),
            precision=0.1,
            initial_value=0.0,
        )
        controller = _create_master(daemon_device_harness,
            MappedController,
            name="mapped_ctrl",
            controlled_device="axis",
            mapping={"ok": 3.0},
        )

        # Act + Assert
        with pytest.raises(LimitError):
            controller.mapping = {"ok": 3.0, "bad": 8.0}

    def test_precision_mapping_returns_nearest_key_within_tolerance(self, daemon_device_harness):
        # Setup
        axis = _create_master(daemon_device_harness,
            HarnessLinearAxis,
            name="axis",
            abslimits=(0.0, 100.0),
            precision=0.2,
            initial_value=10.08,
        )
        controller = _create_master(daemon_device_harness,
            MappedController,
            name="mapped_ctrl",
            controlled_device="axis",
            mapping={"p10": 10.0, "p20": 20.0},
        )

        # Act
        axis.set_readback(10.08)
        mapped = controller.read(0)

        # Assert
        assert mapped == "p10"

    def test_read_returns_in_between_when_unmapped_value_is_outside_precision(
        self, daemon_device_harness
    ):
        # Setup
        axis = _create_master(daemon_device_harness,
            HarnessLinearAxis,
            name="axis",
            abslimits=(0.0, 100.0),
            precision=0.05,
            initial_value=11.2,
        )
        controller = _create_master(daemon_device_harness,
            MappedController,
            name="mapped_ctrl",
            controlled_device="axis",
            mapping={"p10": 10.0, "p20": 20.0},
        )

        # Act
        axis.set_readback(11.2)
        mapped = controller.read(0)

        # Assert
        assert mapped == "In Between"

    @pytest.mark.xfail(
        reason=(
            "TDD: mapped keys that are falsey values should be returned "
            "correctly instead of being treated as 'In Between'."
        ),
        strict=False,
    )
    def test_falsey_mapped_key_is_preserved_on_read(self, daemon_device_harness):
        # Setup
        _create_master(daemon_device_harness,
            HarnessMoveableNoPrecision,
            name="axis",
            abslimits=(-10.0, 10.0),
            initial_value=0.0,
        )
        controller = _create_master(daemon_device_harness,
            MappedController,
            name="mapped_ctrl",
            controlled_device="axis",
            mapping={"": 0.0},
        )

        # Act
        mapped = controller.read(0)

        # Assert
        assert mapped == ""


class TestMultiTargetMappingHarness:
    """Behavior tests for `MultiTargetMapping` with attached channel lists."""

    def test_attached_channels_by_name_are_started_with_tuple_targets(self, daemon_device_harness):
        # Setup
        ch0 = _create_master(daemon_device_harness,
            HarnessLinearAxis,
            name="ch0",
            abslimits=(0.0, 100.0),
            precision=0.1,
            initial_value=0.0,
        )
        ch1 = _create_master(daemon_device_harness,
            HarnessLinearAxis,
            name="ch1",
            abslimits=(0.0, 100.0),
            precision=0.1,
            initial_value=0.0,
        )
        mapping = _create_master(daemon_device_harness,
            MultiTargetMapping,
            name="mtm",
            controlled_devices=["ch0", "ch1"],
            mapping={"focus": (1.5, 2.5)},
        )

        # Act
        mapping.start("focus")

        # Assert
        assert mapping._attached_controlled_devices == [ch0, ch1]
        assert ch0.read(0) == 1.5
        assert ch1.read(0) == 2.5
        assert mapping.read(0) == "focus"

    def test_read_uses_per_channel_precision_for_tuple_mapping(self, daemon_device_harness):
        # Setup
        ch0 = _create_master(daemon_device_harness,
            HarnessLinearAxis,
            name="ch0",
            abslimits=(0.0, 100.0),
            precision=0.2,
            initial_value=1.08,
        )
        ch1 = _create_master(daemon_device_harness,
            HarnessLinearAxis,
            name="ch1",
            abslimits=(0.0, 100.0),
            precision=0.2,
            initial_value=2.05,
        )
        mapping = _create_master(daemon_device_harness,
            MultiTargetMapping,
            name="mtm",
            controlled_devices=["ch0", "ch1"],
            mapping={"focus": (1.0, 2.0)},
        )

        # Act
        ch0.set_readback(1.08)
        ch1.set_readback(2.05)
        mapped = mapping.read(0)

        # Assert
        assert mapped == "focus"

    def test_status_aggregates_attached_channel_status(self, daemon_device_harness):
        # Setup
        ch0 = _create_master(daemon_device_harness,
            HarnessLinearAxis,
            name="ch0",
            abslimits=(0.0, 100.0),
            precision=0.1,
            initial_value=0.0,
        )
        _create_master(daemon_device_harness,
            HarnessLinearAxis,
            name="ch1",
            abslimits=(0.0, 100.0),
            precision=0.1,
            initial_value=0.0,
        )
        mapping = _create_master(daemon_device_harness,
            MultiTargetMapping,
            name="mtm",
            controlled_devices=["ch0", "ch1"],
            mapping={"focus": (1.0, 2.0)},
        )
        ch0.set_status(status.BUSY, "moving")

        # Act
        st = mapping.status(0)

        # Assert
        assert st[0] == status.BUSY

    def test_read_returns_in_between_for_unmapped_tuple(self, daemon_device_harness):
        # Setup
        ch0 = _create_master(daemon_device_harness,
            HarnessLinearAxis,
            name="ch0",
            abslimits=(0.0, 100.0),
            precision=0.05,
            initial_value=1.6,
        )
        ch1 = _create_master(daemon_device_harness,
            HarnessLinearAxis,
            name="ch1",
            abslimits=(0.0, 100.0),
            precision=0.05,
            initial_value=2.4,
        )
        mapping = _create_master(daemon_device_harness,
            MultiTargetMapping,
            name="mtm",
            controlled_devices=["ch0", "ch1"],
            mapping={"focus": (1.0, 2.0)},
        )

        # Act
        ch0.set_readback(1.6)
        ch1.set_readback(2.4)
        mapped = mapping.read(0)

        # Assert
        assert mapped == "In Between"

    def test_falsey_mapped_key_is_preserved_on_read(self, daemon_device_harness):
        # Setup
        _create_master(daemon_device_harness,
            HarnessLinearAxis,
            name="ch0",
            abslimits=(0.0, 100.0),
            precision=0.1,
            initial_value=0.0,
        )
        _create_master(daemon_device_harness,
            HarnessLinearAxis,
            name="ch1",
            abslimits=(0.0, 100.0),
            precision=0.1,
            initial_value=1.0,
        )
        mapping = _create_master(daemon_device_harness,
            MultiTargetMapping,
            name="mtm",
            controlled_devices=["ch0", "ch1"],
            mapping={"": (0.0, 1.0)},
        )

        # Act
        mapped = mapping.read(0)

        # Assert
        assert mapped == ""


class TestSelectorComposerHarness:
    """Integration tests for selector/composer/multi-target attach chains."""

    def _create_chain(self, daemon_device_harness):
        ch0 = _create_master(daemon_device_harness,
            HarnessLinearAxis,
            name="ch0",
            abslimits=(0.0, 100.0),
            precision=0.1,
            initial_value=0.0,
        )
        ch1 = _create_master(daemon_device_harness,
            HarnessLinearAxis,
            name="ch1",
            abslimits=(0.0, 100.0),
            precision=0.1,
            initial_value=0.0,
        )
        out_map = _create_master(daemon_device_harness,
            MultiTargetMapping,
            name="out_map",
            controlled_devices=["ch0", "ch1"],
            mapping={"a,b": (10.0, 20.0), "c,b": (30.0, 20.0)},
        )
        composer = _create_master(daemon_device_harness,
            MultiTargetComposer,
            name="composer",
            out="out_map",
        )
        sel0 = _create_master(daemon_device_harness,
            MultiTargetSelector,
            name="sel0",
            composer="composer",
            idx=0,
            mapping={"A": "a", "C": "c"},
        )
        sel1 = _create_master(daemon_device_harness,
            MultiTargetSelector,
            name="sel1",
            composer="composer",
            idx=1,
            mapping={"B": "b"},
        )
        return ch0, ch1, out_map, composer, sel0, sel1

    def test_selectors_register_with_composer_during_init(self, daemon_device_harness):
        # Setup
        _, _, _, composer, sel0, sel1 = self._create_chain(daemon_device_harness)

        # Assert
        assert composer._selectors == [sel0, sel1]

    def test_composer_requires_all_registered_selectors_to_be_set(self, daemon_device_harness):
        # Setup
        _, _, _, composer, _, _ = self._create_chain(daemon_device_harness)

        # Act + Assert
        with pytest.raises(InvalidValueError):
            composer.start("ignored")

    def test_selector_composer_mapping_chain_drives_underlying_channels(self, daemon_device_harness):
        # Setup
        ch0, ch1, _, composer, sel0, sel1 = self._create_chain(daemon_device_harness)

        # Act
        # First selector alone is not enough and should fail loudly.
        with pytest.raises(InvalidValueError):
            sel0.start("C")
        # Once all selectors have values, the composed key is sent downstream.
        sel1.start("B")

        # Assert
        assert ch0.read(0) == 30.0
        assert ch1.read(0) == 20.0
        assert composer.read(0) == "c,b"
        assert sel0.read(0) == "C"
        assert sel1.read(0) == "B"

    def test_selector_read_propagates_in_between_from_composer_chain(self, daemon_device_harness):
        # Setup
        ch0, ch1, _, _, sel0, _ = self._create_chain(daemon_device_harness)
        ch0.set_readback(99.0)
        ch1.set_readback(99.0)

        # Act
        value = sel0.read(0)

        # Assert
        assert value == "In Between"

    @pytest.mark.xfail(
        reason=(
            "TDD: falsey selector values (e.g. empty string) should be handled "
            "as valid mapped values in composer start logic."
        ),
        strict=False,
    )
    def test_composer_accepts_falsey_selector_values_when_mapping_defines_them(
        self, daemon_device_harness
    ):
        # Setup
        _create_master(daemon_device_harness,
            HarnessLinearAxis,
            name="ch0",
            abslimits=(0.0, 100.0),
            precision=0.1,
            initial_value=0.0,
        )
        _create_master(daemon_device_harness,
            HarnessLinearAxis,
            name="ch1",
            abslimits=(0.0, 100.0),
            precision=0.1,
            initial_value=0.0,
        )
        _create_master(daemon_device_harness,
            MultiTargetMapping,
            name="out_map",
            controlled_devices=["ch0", "ch1"],
            mapping={",b": (11.0, 22.0)},
        )
        _create_master(daemon_device_harness,
            MultiTargetComposer,
            name="composer",
            out="out_map",
        )
        sel0 = _create_master(daemon_device_harness,
            MultiTargetSelector,
            name="sel0",
            composer="composer",
            idx=0,
            mapping={"EMPTY": ""},
        )
        sel1 = _create_master(daemon_device_harness,
            MultiTargetSelector,
            name="sel1",
            composer="composer",
            idx=1,
            mapping={"B": "b"},
        )

        # Act
        with pytest.raises(InvalidValueError):
            sel0.start("EMPTY")
        sel1.start("B")

        # Assert
        assert sel1.read(0) == "B"
