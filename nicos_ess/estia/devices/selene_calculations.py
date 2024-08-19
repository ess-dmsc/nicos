"""
Help module that is used for calculations in SeleneMetrology
this allows off-line and unit testing.
"""

import numpy as np
from numpy import testing
from unittest import TestCase


class SeleneCalculator:
    _sb = 104.7  # selene distance center-ellipse
    _sc = 6000.0  # selene distance center-focus
    _sa = np.sqrt(_sc**2 + _sb**2)

    _mw = 480.0  # mirror width
    _sx = 42.5  # distance of screw from edge of mirror

    # these attributes will be overwritte in device
    eta_v = 14.92
    delta_v = 120.0
    delta_x = -15.0

    eta_h1 = 16.39
    delta_h1 = 70.0
    zret_h1 = 50.0
    zcol_h1 = 120.0
    eta_h2 = 15.47
    delta_h2 = 80.0
    zret_h2 = 10.0
    zcol_h2 = 160.0

    col_h1 = (46.0, -135.0, 143.5)
    ret_h1 = (-15.0, -70.0, 62.5)
    col_h2 = (44.5, -132.4, 201.5)
    ret_h2 = (-15.0, -80.0, 17)

    def _ellipse(self, xpos):
        # return selene ellipse height at distance from center
        return self._sb / self._sa * np.sqrt(self._sa**2 - xpos**2)

    def _ellipse_angle(self, xpos):
        # return the inclanation of the ellipse at defined position
        return -self._sb * xpos / (self._sa * np.sqrt(self._sa**2 - xpos**2))

    def _cart_for_x(self, xpos, zero_range=True):
        """
        Calculate the cart position necessary to measure at a certain x-positin on the ellipse.
        This has to take into account the location of the correct interferometer heads
        and the change in reflection spot location due to ellipse surface changing distance to cart.
        """
        if zero_range and abs(xpos) < 100.0:
            # if around center of guide, don't perform any correction
            return xpos
        # In the optimal configuration the retro reflector receives the beam with
        # half of the nominal angle plus 2x the surface inclination.
        alpha = self.eta_v * np.pi / 360.0 - self._ellipse_angle(abs(xpos)) / 2.0
        # distance of that reflection is the nominal distance at center minus ellipse height
        h = self.delta_v + self._ellipse(xpos)
        div = self.delta_x + np.tan(alpha) * h
        direction = np.sign(
            xpos
        )  # select if up-stream or down-stream collimators are used
        return xpos - direction * div

    def _x_for_cart(self, xpos):
        """
        Calculate the approximate position the laser hits the mirror
        for a given cart position
        """
        delta = 100.0
        xout = xpos
        while delta > 1.0:
            dpos = self._cart_for_x(xout, zero_range=False) - xpos
            xout -= dpos
            delta = abs(dpos)
        return xout

    def _diagnoal_paths(self, xpos, col, ret):
        ye = self._ellipse(xpos)
        # both beams should come under ~45°, so y/z-positions are equal to z/y-distance
        x_total = col[0] - ret[0]
        z_total = (ye - col[1]) + (ye - ret[1])
        rel_1 = (ye - col[1]) / z_total
        rel_2 = (ye - ret[1]) / z_total
        p1 = np.array([ret[0] + rel_1 * x_total, ye, col[2] - (ye - col[1])])
        p2 = np.array([ret[0] + rel_2 * x_total, -p1[2], -ye])
        return p1, p2

    def _nominal_path_lengths(self, pos_motor=None):
        """
        Calculate the individual laser path lengths that would be excepted
        if the mirrors are perfectly aligned.
        """
        if pos_motor is None:
            pos_motor = self._attached_m_cart() - self.cart_center
        xpos = self._x_for_cart(pos_motor)
        # length of laser is distance reflector-mirror + collimator-mirror
        # vertical mirrors
        dalpha = self._ellipse_angle(abs(xpos)) / 2.0
        ye = self._ellipse(xpos)
        h = self.delta_v + ye
        v_l1 = h / np.cos(
            self.eta_v / 2 * np.pi / 180.0 + dalpha
        )  # reflector angle gets larger
        v_l2 = h / np.cos(
            self.eta_v / 2 * np.pi / 180.0 - dalpha
        )  # collimator angle gets smaller

        # for diagnoal paths, 3d has to be considered and two reflections
        # horizontal w/ short path
        # h1_ret = np.array([self.delta_x, -self.delta_h1, self.zret_h1])
        # h1_col = np.array([self.delta_x+2*(self.delta_h1+self._sb)*np.tan(self.eta_h1/2*np.pi/180.),
        #                    -self.delta_h1, self.zcol_h1])
        h1_ret = np.array(self.ret_h1)
        h1_col = np.array(self.col_h1)
        h1_p1, h1_p2 = self._diagnoal_paths(xpos, h1_col, h1_ret)
        if hasattr(self, "log"):
            self.log.debug(f"Calculated path: {h1_col}->{h1_p1}->{h1_p2}->{h1_ret}")
        h1_l1 = np.sqrt(((h1_col - h1_p1) ** 2).sum())
        h1_l2 = np.sqrt(((h1_p1 - h1_p2) ** 2).sum())
        h1_l3 = np.sqrt(((h1_p2 - h1_ret) ** 2).sum())

        # horizontal w/ long path
        # h2_ret = np.array([self.delta_x, -self.delta_h2, self.zret_h2])
        # h2_col = np.array([self.delta_x+2*(self.delta_h2+self._sb)*np.tan(self.eta_h2/2*np.pi/180.),
        #                    -self.delta_h2, self.zcol_h2])
        h2_ret = np.array(self.ret_h2)
        h2_col = np.array(self.col_h2)
        h2_p1, h2_p2 = self._diagnoal_paths(xpos, h2_col, h2_ret)
        if hasattr(self, "log"):
            self.log.debug(f"Calculated path: {h2_col}->{h2_p1}->{h2_p2}->{h2_ret}")
        h2_l1 = np.sqrt(((h2_col - h2_p1) ** 2).sum())
        h2_l2 = np.sqrt(((h2_p1 - h2_p2) ** 2).sum())
        h2_l3 = np.sqrt(((h2_p2 - h2_ret) ** 2).sum())

        return (v_l1 + v_l2, h1_l1 + h1_l2 + h1_l3, h2_l1 + h2_l2 + h2_l3)

    def _path_delta_to_screw_delta(self, dv1, dv2, dh1, dh2):
        """
        Calculate the expected mirror offset at the screw locations
        that lead to the measured path length difference.
        """
        # approximate offset based on reflection angle at center
        # maximum deviation is <1% over full ellipse range
        fac = 1.0 / np.cos(self.eta_v / 2 * np.pi / 180.0)
        dpos_v1 = dv1 / 2 * fac
        dpos_v2 = dv2 / 2 * fac
        # The diagonal beam path is dominated by the 45° angle in vertical
        # plane, horionzontal deviation is thus ignored. But both mirrors
        # have influence on measured length.
        fac = 1.0 / np.cos(np.pi / 4.0)
        dpos_h1 = dh1 / 2 * fac - (dpos_v1 + dpos_v2) / 2
        dpos_h2 = dh2 / 2 * fac - (dpos_v1 + dpos_v2) / 2
        # TODO: include the location of the screws in the horizontal calculation
        c2_z = 40.0
        c1_z = 80.0
        s2_z = 17.5
        s1_z = 123.5
        dd_v = (dpos_v2 - dpos_v1) / (c2_z - c1_z)
        spos_v1 = (s1_z - c1_z) * dd_v + dpos_v1
        spos_v2 = (s2_z - c1_z) * dd_v + dpos_v1
        return spos_v1, spos_v2, dpos_h1, dpos_h2


class CalcTester(TestCase):
    calc: SeleneCalculator

    def setUp(self):
        self.calc = SeleneCalculator()

    def test_ellipse(self):
        y = self.calc._ellipse(0.0)
        self.assertAlmostEqual(y, self.calc._sb)

    def test_cartx(self):
        # test that the x-position conversion is inverse
        x = np.linspace(-3500, 3500, 25)
        xcart = []
        for xi in x:
            xcart.append(self.calc._cart_for_x(xi, zero_range=False))
        xr = []
        for xi in xcart:
            xr.append(self.calc._x_for_cart(xi))
        testing.assert_array_almost_equal(x, np.array(xr), decimal=2)

    def test_lengths(self):
        class Bla:
            debug = print

        log = Bla()
        self.calc.log = log
        self.calc._nominal_path_lengths(0.0)
