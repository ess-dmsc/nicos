from nicos.core import (
    Attach,
    HasMapping,
    Moveable,
    Override,
    Param,
    anytype,
    none_or,
    status,
)
from nicos.devices.generic import BaseSequencer
from nicos.devices.generic.sequence import SeqDev, SeqMethod


class BeamStopSequencer(HasMapping, BaseSequencer):
    """
    Sequencer for four beamstop motors.

    Target values (via mapping) should be one of:
        - 'bs1', 'bs2', 'bs3', 'bs4'  (meaning: move that beamstop IN)
        - 'out'                       (meaning: move all OUT)

    Each attached beamstop is an analog Moveable. Positions:
        - IN  => inpos (default 0.0 mm)
        - OUT => outpos (default 15.0 mm)
    """

    attached_devices = {
        "bs1": Attach("The first beamstop", Moveable),
        "bs2": Attach("The second beamstop", Moveable),
        "bs3": Attach("The third beamstop", Moveable),
        "bs4": Attach("The fourth beamstop", Moveable),
    }

    parameters = {
        "inpos": Param(
            "Position [mm] that corresponds to 'in'", type=float, default=0.0
        ),
        "outpos": Param(
            "Position [mm] that corresponds to 'out'", type=float, default=15.0
        ),
    }

    parameter_overrides = {
        "unit": Override(mandatory=False, default=""),
    }

    def _all_beamstops(self):
        return [
            self._attached_bs1,
            self._attached_bs2,
            self._attached_bs3,
            self._attached_bs4,
        ]

    def _resolve_target(self, target):
        """
        Resolve a user-facing target via HasMapping.mapping.
        Expect mapping to map friendly keys -> {'bs1','bs2','bs3','bs4','out'}.
        If target is already one of those, just pass it through.
        """
        try:
            return self.mapping[target]
        except Exception:
            return target

    def _safe_read(self, dev):
        try:
            return float(dev.read(0))
        except Exception:
            return None

    def _is_at(self, dev, position):
        val = self._safe_read(dev)
        return (val is not None) and (abs(val - position) <= dev.precision)

    def _key_for_value(self, val):
        """Return mapping key for a mapped value; fall back to the value itself."""
        for k, v in self.mapping.items():
            if v == val:
                return k
        return val

    def doRead(self, maxage=0):
        """Return which beamstop is IN according to tolerance, or 'out'."""
        for name in ("bs1", "bs2", "bs3", "bs4"):
            dev = getattr(self, f"_attached_{name}")
            if self._is_at(dev, self.inpos):
                # return the *key* users expect (mapping key), not the raw value
                return self._key_for_value(name)
        return self._key_for_value("out")

    def _generateSequence(self, target):
        """
        Policy:
        - If requested beamstop is already IN (within tol), do nothing.
        - Else: move all OUT, then move requested one IN (if not 'out').
        """
        print(f"Generating sequence to move to target '{target}'")
        seq = []

        resolved = self._resolve_target(target)  # 'bs1'..'bs4' or 'out'
        all_bs = self._all_beamstops()

        # Determine desired device (or None for 'out')
        desired = (
            None
            if resolved in (None, "out")
            else getattr(self, f"_attached_{resolved}", None)
        )

        # Fast-path: if the requested one is already IN, do nothing.
        if desired is not None and self._is_at(desired, self.inpos):
            print(f"  -> '{target}' is already IN; no action needed")
            return seq  # empty sequence

        # Step 1: move all beamstops OUT (only those not already out)
        move_out_actions = tuple(
            SeqDev(dev, self.outpos)
            for dev in all_bs
            if not self._is_at(dev, self.outpos)
        )
        for action in move_out_actions:
            seq.append(action)

        # Step 2: move the requested beamstop IN (if any)
        if desired is not None:
            seq.append(SeqDev(desired, self.inpos))

        print(f"Generated sequence: {seq}")

        return seq
