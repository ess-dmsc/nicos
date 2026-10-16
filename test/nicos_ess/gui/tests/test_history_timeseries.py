"""Replay cache updates through the real ESS history view."""

import numpy as np

from nicos.utils import parseKeyExpression
from nicos_ess.gui.panels.history import View


# Rollover also fails at merge base 11eee37ee1 due to its invalid resize() call;
# this MR fails earlier because the lttbc API call is incorrect.
def test_live_history_without_sliding_window_survives_three_days(gui_window):
    # _createViewFromDialog() uses window=None for a live view when the user
    # unchecks slidingWindow (or selects no start/end dates). No history query
    # is needed when fromtime=None; updates enter through View.newValue().
    keys, exprs, descs = parseKeyExpression("temperature", multiple=True)
    view = View(
        widget=gui_window,
        name="temperature",
        keys=keys,
        exprs=exprs,
        descs=descs,
        interval=2,
        fromtime=None,
        totime=None,
        yfrom=None,
        yto=None,
        window=None,
        meta=({}, {}),
        dlginfo={},
        query_func=None,
    )
    view.setParent(gui_window)
    start = 1_700_000_000.0
    count = 128001
    updates = 0

    def record_update(series):
        nonlocal updates
        updates += 1

    view.timeSeriesUpdate.connect(record_update)
    try:
        for index in range(count):
            view.newValue(
                start + index * 2, "temperature/value", "=", 20 + index * 0.0001
            )

        series = view.series["temperature/value", None]
        assert updates == count
        assert series.x[0] == start
        assert series.x[-1] == start + (count - 1) * 2
        assert np.all(np.diff(series.x) > 0)
        np.testing.assert_allclose(series.y, 20 + (series.x - start) / 2 * 0.0001)
    finally:
        view.timer.stop()
        view.deleteLater()
