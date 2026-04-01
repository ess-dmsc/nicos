from unittest import TestCase
import pytest
import numpy as np
from numpy import testing
from nicos_ess.estia.devices.selene_calculations import SeleneCalculator
from nicos.devices.generic import BaseSequencer

session_setup = "estia_selene_calculations"

class FakeSeleneCalculator(SeleneCalculator, BaseSequencer):
    pass



class TestCalculator(TestCase):

    @pytest.fixture(autouse=True)
    def prepare(self, session):
        self.session = session
        self.calc = self.session.getDevice("selene_calculator")

    def test_ellipse(self):
        y = self.calc._ellipse(0.0)
        self.assertAlmostEqual(y, self.calc._ellipse_semi_minor_axis)

    def test_ellipse_angle(self):
        zero_angle = self.calc._ellipse_gradient(0.0)
        self.assertAlmostEqual(zero_angle, 0.0)

        end_angle = self.calc._ellipse_gradient(5000)
        self.assertAlmostEqual(end_angle, -0.0262897641)

    def test_cartx(self):
        # test that the x-position conversion is inverse
        x = np.linspace(-3500, 3500, 25)
        xcart = []
        for xi in x:
            xcart.append(self.calc._cart_pos_correction(xi, zero_range=False))
        xr = []
        for xi in xcart:
            xr.append(self.calc._laser_pos_from_cart(xi))
        testing.assert_array_almost_equal(x, np.array(xr), decimal=2)

    def test_lengths(self):
        length_0 = self.calc._nominal_path_lengths(0.0)
        testing.assert_allclose(
            length_0, np.array([453.23630804, 592.47373481, 604.18396285])
        )
        length_5000 = self.calc._nominal_path_lengths(5000.0)
        testing.assert_allclose(
            length_5000, np.array([358.29303101, 461.63617516, 472.40071283])
        )

    def test_laser_pos_from_cart(self):
        pos1 = self.calc._laser_pos_from_cart(1.0)
        self.assertAlmostEqual(pos1, 15.42782082100291)
        pos2 = self.calc._laser_pos_from_cart(1500.6)
        self.assertAlmostEqual(pos2, 1515.0911359578206)

    def test_path_delta_to_screw_delta(self):
        screw1 = self.calc._path_delta_to_screw_delta(1, 2, 3, 4)
        testing.assert_allclose(
            screw1, [-0.04412347, 1.2921874, 1.36491796, 2.07202474]
        )

        screw2 = self.calc._path_delta_to_screw_delta(18, 0, 30, 45)
        testing.assert_allclose(
            screw2, [18.9478797, -5.10571609, 16.67478914, 27.28139085]
        )
