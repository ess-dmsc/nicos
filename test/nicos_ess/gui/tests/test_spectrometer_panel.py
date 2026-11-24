import numpy as np
import pytest

from nicos.core.constants import LIVE
from nicos.guisupport.qt import Qt
from nicos_ess.loki.gui.panels.spectrometer import BLUE, SpectrometerPanel
from nicos_ess.utilities.live_frame import curve_frame, encode
from test.nicos_ess.gui.doubles import DeviceSpec
from test.nicos_ess.gui.helpers import get_panel_by_class, single_panel_guiconfig_string

PARAMS = dict(
    _wavelengths=[400.0, 500.0, 600.0],
    _spectrum_array=[1.0, 2.0, 3.0],
    _light_array=[1.0, 1.0, 1.0],
    _dark_array=[0.1, 0.1, 0.1],
    acquireunits="ms",
    status=(0, "Idle"),
    darkvalid=True,
    lightvalid=True,
    integrationtime=10.0,
    boxcarwidth=1,
    acquiremode="single",
)


@pytest.fixture
def panel(gui_window_factory, fake_daemon):
    for name in ("hr4", "qepro"):
        fake_daemon.add_device(DeviceSpec(name=name, valuetype=float, params=PARAMS))
    window = gui_window_factory(
        guiconfig_string=single_panel_guiconfig_string(SpectrometerPanel)
    )
    return get_panel_by_class(window, SpectrometerPanel)


# These helpers keep the access to the inner plot widgets in one place.
def drawn_values(panel):
    return panel.plot.curve.line.yData


def drawn_wavelengths(panel):
    return panel.plot.curve.line.xData


def wavelength_unit(panel):
    return panel.plot.plot.getAxis("bottom").labelUnits


def set_background(panel, kind, values):
    panel.arrays[kind] = np.array(values)


def push_spectrum(qtbot, panel, fake_daemon, desc, blobs):
    desc["array_type"] = "normal"
    params = dict(det="hr4", tag=LIVE, datadescs=[desc])
    with qtbot.waitSignal(panel.client.livedata):
        fake_daemon.push("livedata", params, blobs)


def test_live_spectrum_without_a_unit_has_no_wavelength_unit(panel, fake_daemon, qtbot):
    data = np.array([4.0, 5.0, 6.0], dtype="<f4")
    x = dict(define="range", start=400.0, length=3, step=100.0)
    desc = dict(shape=(3,), dtype="<f4", labels={"x": x})

    push_spectrum(qtbot, panel, fake_daemon, desc, [data.tobytes()])

    qtbot.waitUntil(lambda: np.array_equal(drawn_values(panel), data))
    assert list(drawn_wavelengths(panel)) == [400.0, 500.0, 600.0]
    assert wavelength_unit(panel) == ""


def test_live_spectrum_shows_the_wavelength_unit_it_brings(panel, fake_daemon, qtbot):
    data = np.array([4.0, 5.0, 6.0])
    frame = curve_frame("wavelength", "counts", [400.0, 500.0, 600.0], data, "nm")
    datadescs, buffers, labels = encode([frame])

    push_spectrum(qtbot, panel, fake_daemon, datadescs[0], buffers + labels)

    qtbot.waitUntil(lambda: np.array_equal(drawn_values(panel), data))
    assert wavelength_unit(panel) == "nm"


@pytest.mark.parametrize(
    "mode, expected",
    [
        # The panel draws light minus spectrum on purpose.
        ("subtraction", [0.0, -1.0, -2.0]),
        ("absorbance", np.log10([0.9 / 0.9, 0.9 / 1.9, 0.9 / 2.9])),
    ],
)
def test_corrected_spectra_are_computed_from_the_backgrounds(panel, mode, expected):
    panel.draw(mode)
    np.testing.assert_allclose(drawn_values(panel), expected)


def test_readbacks_follow_the_cache_without_repolling(panel, fake_daemon, qtbot):
    controller = panel.spectrometer_controller
    # The panel selects the first spectrometer when it connects.
    assert controller.detector_combo.currentText() == "hr4"
    assert controller.integration_time.readback.text() == "10.0"

    fake_daemon.command_log.clear()
    fake_daemon.push_cache("hr4/integrationtime", 25.0)

    qtbot.waitUntil(lambda: controller.integration_time.readback.text() == "25.0")
    assert controller.boxcar_width.readback.text() == "1"
    polls = [a for c, a in fake_daemon.command_log if c == "eval" and a]
    assert "hr4.pollParams()" not in [a[0] for a in polls]


def test_cache_keys_of_the_other_spectrometer_are_ignored(panel, fake_daemon, qtbot):
    controller = panel.spectrometer_controller
    fake_daemon.push_cache("qepro/integrationtime", 99.0)
    # The cache delivers keys in order, so this key arrives after the qepro key.
    fake_daemon.push_cache("hr4/boxcarwidth", 3)

    qtbot.waitUntil(lambda: controller.boxcar_width.readback.text() == "3")
    assert controller.integration_time.readback.text() == "10.0"


def test_an_invalid_light_background_shows_a_warning(panel, fake_daemon, qtbot):
    warning = panel.spectrometer_controller.valid_labels["lightvalid"]
    assert warning.isHidden()

    fake_daemon.push_cache("hr4/lightvalid", False)

    qtbot.waitUntil(lambda: not warning.isHidden())
    assert panel.spectrometer_controller.valid_labels["darkvalid"].isHidden()


@pytest.mark.parametrize(
    "mode, kind", [("subtraction", "lightbackground"), ("absorbance", "darkbackground")]
)
def test_a_background_of_another_length_draws_nothing(panel, mode, kind):
    panel.draw(mode)
    assert not panel.plot.empty_note.isVisible()
    for background in ([], [1.0, 1.0]):
        set_background(panel, kind, background)
        panel.draw(mode)
        assert panel.plot.empty_note.isVisible()


def test_only_a_number_typed_into_a_field_is_sent(panel, fake_daemon, qtbot):
    field = panel.spectrometer_controller.integration_time
    for text in ("abc", "1e400", "25"):
        field.clear()
        qtbot.keyClicks(field, text)
        qtbot.keyClick(field, Qt.Key.Key_Return)

    assert fake_daemon.sent_scripts("exec") == ["hr4.integrationtime = 25.000000"]


def test_an_acquire_mode_from_the_cache_is_not_sent_back(panel, fake_daemon, qtbot):
    combo = panel.spectrometer_controller.acq_mode_combo
    fake_daemon.push_cache("hr4/acquiremode", "continuous")
    qtbot.waitUntil(lambda: combo.currentText() == "continuous")
    assert fake_daemon.sent_scripts("exec") == []

    qtbot.keyClick(combo, Qt.Key.Key_Up)
    assert fake_daemon.sent_scripts("exec") == ['hr4.acquiremode = "single"']


def test_data_of_the_wrong_shape_is_ignored(panel, fake_daemon, qtbot):
    controller = panel.spectrometer_controller
    fake_daemon.set_cache("qepro/status", None)
    fake_daemon.evals["qepro._spectrum_array"] = 5
    fake_daemon.evals["qepro._light_array"] = [10**400, 1.0, 2.0]
    controller.detector_combo.setCurrentText("qepro")
    assert panel.plot.empty_note.isVisible()

    fake_daemon.push_cache("qepro/status", (400, 5))
    fake_daemon.push_cache("qepro/status", (200, "Acquiring"))
    qtbot.waitUntil(lambda: BLUE in controller.start_acq_button.styleSheet())


def test_livedata_without_a_detector_name_is_ignored(panel, fake_daemon, qtbot):
    with qtbot.waitSignal(panel.client.livedata):
        fake_daemon.push("livedata", dict(tag=LIVE, datadescs=[]), [])
