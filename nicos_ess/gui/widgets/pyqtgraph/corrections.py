"""Background subtraction and flat-field division of an image."""

from dataclasses import replace

import numpy as np

from nicos_ess.gui.widgets.pyqtgraph.frame_format import close

SHOWN = ("image", "background", "flat field")


def _divide_by_flat(values, flat, background):
    """Return *values* divided by the *flat* field minus the *background*.

    Bins where the flat field minus the background is zero or not finite
    become NaN.
    """
    if background is not None:
        flat = flat - background
    divided = np.full(values.shape, np.nan)
    valid = np.isfinite(flat) & (flat != 0)
    return np.divide(values, flat, out=divided, where=valid)


class Corrections:
    """Corrections of one image output with references taken from it.

    Nothing is saved because the settings mean nothing without the references.
    A reference only applies to images with the same bin edges, which means
    the same camera binning and area. A reference keeps the exposure in
    seconds that it was taken at, or None if that is unknown. `apply` says
    when the exposure differs.
    """

    def __init__(self):
        self.forget()

    def take(self, which, values, edges, exposure):
        """Keep *values* on bin *edges* (x, y) as the "background" or "flat field".

        *exposure* is the exposure the reference was taken at.
        """
        self.references[which] = np.array(values, dtype=float)
        self.edges[which], self.exposures[which] = edges, exposure

    def forget(self):
        self.references = dict.fromkeys(SHOWN[1:])
        self.edges = dict.fromkeys(SHOWN[1:])
        self.exposures = dict.fromkeys(SHOWN[1:])
        self.subtract = self.divide = False
        self.shown = "image"

    def _fits(self, which, edges):
        return self.references[which] is not None and all(
            close(a, b) for a, b in zip(self.edges[which], edges, strict=True)
        )

    def _exposure_notes(self, which, now):
        taken = self.exposures[which]
        if None not in (taken, now) and abs(taken - now) > 1e-9 * max(now, 1):
            return [f"{which} taken at {taken:g} s, exposure now {now:g} s"]
        return []

    def apply(self, view, edges):
        """Return the image *view* on bin *edges* (x, y) corrected, and a note.

        The view comes back unchanged if no correction applies. A corrected
        view has no errors. A division by the flat field gives the transmission,
        a ratio that has no unit and is no count. When a reference is shown it
        is returned instead of
        the values. The note says which corrections could not be applied and
        which reference was taken at another exposure than the view.
        """
        if self.shown != "image":
            if not self._fits(self.shown, edges):
                return view, f"no {self.shown} taken at this binning"
            return replace(view, data=self.references[self.shown], errors=None), ""
        raw = values = np.asarray(view.data, dtype=float)
        unit, counts, now = view.unit, view.counts, view.meta.get("exposure")
        notes, below = [], None
        for on, which in ((self.subtract, "background"), (self.divide, "flat field")):
            reference = self.references[which]
            if not on:
                continue
            if not self._fits(which, edges):
                why = "none taken" if reference is None else "taken at another binning"
                notes.append(f"{which} not applied: {why}")
                continue
            notes += self._exposure_notes(which, now)
            if which == "background":
                values, below = values - reference, reference
            else:
                values = _divide_by_flat(values, reference, below)
                unit, counts = "", False
        if values is raw:
            return view, "; ".join(notes)
        corrected = replace(view, data=values, errors=None, unit=unit, counts=counts)
        return corrected, "; ".join(notes)

    def applied(self):
        """Return the active corrections as text for the title."""
        if self.shown != "image":
            return [f"showing the {self.shown}"]
        return ["− background"] * self.subtract + ["÷ flat"] * self.divide
