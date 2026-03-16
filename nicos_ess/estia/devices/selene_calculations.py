"""
Help module that is used for calculations in Selene Metrology
this allows off-line and unit testing.
"""

from unittest import TestCase

import numpy as np
from numpy import testing


class SeleneCalculator:
    """
    Calculations for moving the metronomy cart and correcting the mirror positions.
    All angles are in degrees, all distances are in mm.
    """

    def __init__(self):
        self._ellipse_semi_minor_axis = 104.7
        self._ellipse_linear_eccentricity = 6000.0
        self._ellipse_semi_major_axis = np.sqrt(
            self._ellipse_linear_eccentricity**2 + self._ellipse_semi_minor_axis**2
        )
        self._ellipse_eccentricity = (
            self._ellipse_semi_minor_axis / self._ellipse_semi_major_axis
        )

        self._mirror_width = 480.0
        self._screw_mirror_dist = 42.5

        # these attributes will be overwritten in device
        self.inter_to_retro_horiz_angle = 14.92
        self.xz_to_retro_horiz_dist = 120.0
        self.x_dist_to_cart_centre = -15.0

        self.inter_to_retro_1_angle = 16.39
        self.xz_to_retro_1_dist = 70.0
        self.xy_to_retro_1_dist = 50.0
        self.xy_to_col_1_dist = 120.0
        self.inter_to_retro_2_angle = 15.47
        self.xz_to_retro_2_dist = 80.0
        self.xy_to_retro_2_dist = 10.0
        self.xy_to_col_2_dist = 160.0

        self.collimator_1_pos = (46.0, -135.0, 143.5)
        self.retro_1_pos = (-15.0, -70.0, 62.5)
        self.collimator_2_pos = (44.5, -132.4, 201.5)
        self.retro_2_pos = (-15.0, -80.0, 17)

    def _ellipse(self, x_pos):
        """
        Gives the ellipse height at distance xpos from center
        Parameters:
            x_pos: float, position along ellipse in mm

        Returns:
             float, height at that position in mm
        """
        return self._ellipse_eccentricity * np.sqrt(
            self._ellipse_semi_major_axis**2 - x_pos**2
        )

    def _ellipse_gradient(self, x_pos):
        """
        Gives the ellipse tangent at distance xpos from center
        Parameters:
            x_pos: float, position along ellipse in mm

        Returns:
             float, gradient of the tangent to the ellipse at given position
        """
        return (
            -self._ellipse_eccentricity
            * x_pos
            / np.sqrt(self._ellipse_semi_major_axis**2 - x_pos**2)
        )

    def _cart_pos_correction(self, x_pos, zero_range=True):
        """
        Calculate the cart position necessary to measure at a certain x-position on the
        ellipse. This has to take into account the location of the correct
        interferometer heads and the change in reflection spot location due to ellipse
        surface changing distance to cart.

        Parameters:
            x_pos: float, position along the ellipse in mm
            zero_range: bool, flag to apply no correction when within the
            central 100 mm, defaults to True
        Returns:
            float, correct position to move the cart to in mm
        """
        if zero_range and abs(x_pos) < 100.0:
            # if around center of guide, don't perform any correction
            return x_pos

        # In the optimal configuration the retro reflector receives the beam with
        # half of the nominal angle plus 2x the surface inclination.
        alpha_angle = (self.inter_to_retro_horiz_angle * np.pi / 360.0) - (
            self._ellipse_gradient(abs(x_pos)) / 2.0
        )

        # distance of that reflection is the nominal distance at center minus
        # ellipse height
        h = self.xz_to_retro_horiz_dist + self._ellipse(x_pos)
        div = self.x_dist_to_cart_centre + np.tan(alpha_angle) * h
        direction = np.sign(
            x_pos
        )  # select if up-stream or down-stream collimators are used
        return x_pos - direction * div

    def _laser_pos_from_cart(self, initial_cart_pos):
        """
        Calculate the approximate position the laser hits the mirror
        for a given cart position (to within 1 mm)
        Parameters:
            initial_cart_pos: float, cart position along the ellipse in mm

        Returns:
            float, laser position along the ellipse in mm
        """
        delta = 100.0
        laser_pos = initial_cart_pos
        while delta > 1.0:
            pos_correction = (
                self._cart_pos_correction(laser_pos, zero_range=False)
                - initial_cart_pos
            )
            laser_pos -= pos_correction
            delta = abs(pos_correction)
        return laser_pos

    def _diagonal_paths(self, x_pos, collimator_pos, retro_pos):
        """
        Calculate the relative coordinates of the points at which the laser will strike
        the mirrors in the frame of the metrology cart (e.g. without x_pos translation)
        Parameters:
            x_pos: float, cart position along the ellipse in mm
            collimator_pos: list[float], coordinates of the collimator
            retro_pos: list[float], coordinates of the retro-reflector
        Returns:
            tuple[list[float]] relative coordinates of the two reflection positions
        """
        ellipse_height = self._ellipse(x_pos)
        # both beams should come under ~45°, so y/z-positions are equal to z/y-distance
        x_total = collimator_pos[0] - retro_pos[0]

        # Path length from collimator to retro-reflector in z
        z_total = (ellipse_height - collimator_pos[1]) + (ellipse_height - retro_pos[1])

        # Relative path lengths to the collimator and retro-reflector
        relative_coll_pos = (ellipse_height - collimator_pos[1]) / z_total
        relative_retro_pos = (ellipse_height - retro_pos[1]) / z_total

        reflection_coord_1 = np.array(
            [
                retro_pos[0] + relative_coll_pos * x_total,
                ellipse_height,
                collimator_pos[2] - (ellipse_height - collimator_pos[1]),
            ]
        )

        reflection_coord_2 = np.array(
            [
                retro_pos[0] + relative_retro_pos * x_total,
                -reflection_coord_1[2],
                -ellipse_height,
            ]
        )

        return reflection_coord_1, reflection_coord_2

    def _nominal_path_lengths(self, pos_motor=None):
        """
        Calculate the laser path lengths for each of the collimator/retro-reflector
        pairs which would be excepted if the mirrors are perfectly aligned.
        Parameters:
            pos_motor: float, position of the cart
        Returns:
            tuple[float, float, float] path lengths for vert_mirror,
            horiz_mirror_beam_1, horiz_mirror_beam_2
        """
        if pos_motor is None:
            pos_motor = self._attached_m_cart() - self.cart_centre
            # I'm not a fan ^ these attributes only exist in a class which
            # inherits this one
        x_pos = self._laser_pos_from_cart(pos_motor)
        # length of laser path is: reflector->mirror + collimator->mirror distances
        # Calculation for vertical mirrors:
        ellipse_half_angle = (
            self._ellipse_gradient(abs(x_pos)) / 2.0
        )  # Small angle approximation, angle in radians
        ellipse_height = self._ellipse(x_pos)
        triangle_height = self.xz_to_retro_horiz_dist + ellipse_height

        # One angle will get larger, the other smaller as you move along the ellipse.
        # They are summed so it doesn't matter which is the
        # collimator-> mirror distance or the retro-reflector->mirror
        vert_mirror_length_1 = triangle_height / np.cos(
            np.radians(self.inter_to_retro_horiz_angle) / 2.0 + ellipse_half_angle
        )
        vert_mirror_length_2 = triangle_height / np.cos(
            np.radians(self.inter_to_retro_horiz_angle) / 2.0 - ellipse_half_angle
        )
        vert_mirror_distance = vert_mirror_length_1 + vert_mirror_length_2

        # For the horizontal mirrors we have to consider the 3D path and two mirror
        # reflections horizontal mirror shorter path
        retro_1_pos_array = np.array(self.retro_1_pos)
        collimator_1_pos_array = np.array(self.collimator_1_pos)
        mirror_reflect_1, mirror_reflect_2 = self._diagonal_paths(
            x_pos, collimator_1_pos_array, retro_1_pos_array
        )
        if hasattr(self, "log"):
            self.log.debug(
                f"\nCalculated path: {collimator_1_pos_array}->{mirror_reflect_1}->{mirror_reflect_2}->{retro_1_pos_array}"
            )
        horiz_mirror_path_1 = np.sqrt(
            ((collimator_1_pos_array - mirror_reflect_1) ** 2).sum()
        )
        horiz_mirror_path_2 = np.sqrt(
            ((mirror_reflect_1 - mirror_reflect_2) ** 2).sum()
        )
        horiz_mirror_path_3 = np.sqrt(
            ((mirror_reflect_2 - retro_1_pos_array) ** 2).sum()
        )
        horiz_mirror_short_path_length = (
            horiz_mirror_path_1 + horiz_mirror_path_2 + horiz_mirror_path_3
        )

        # horizontal mirror longer path
        h2_ret = np.array(self.retro_2_pos)
        h2_col = np.array(self.collimator_2_pos)
        h2_p1, h2_p2 = self._diagonal_paths(x_pos, h2_col, h2_ret)
        if hasattr(self, "log"):
            self.log.debug(f"Calculated path: {h2_col}->{h2_p1}->{h2_p2}->{h2_ret}")
        horiz_mirror_path_4 = np.sqrt(((h2_col - h2_p1) ** 2).sum())
        horiz_mirror_path_5 = np.sqrt(((h2_p1 - h2_p2) ** 2).sum())
        horiz_mirror_path_6 = np.sqrt(((h2_p2 - h2_ret) ** 2).sum())
        horiz_mirror_long_path_length = (
            horiz_mirror_path_4 + horiz_mirror_path_5 + horiz_mirror_path_6
        )

        return (
            vert_mirror_distance,
            horiz_mirror_short_path_length,
            horiz_mirror_long_path_length,
        )

    def _path_delta_to_screw_delta(
        self,
        path_delta_vert_1,
        path_delta_vert_2,
        path_delta_horiz_1,
        path_delta_horiz_2,
    ):
        """
        Calculate the expected mirror offset at the screw locations
        that lead to the measured path length difference.

        From the measured path differences, calculate the required change to the screw
        positions which would bring the mirrors back into the nominal aligned position.
        This returns four values, two for each of the horizontal and vertical mirrors.
        There are three screws on each of the mirrors, so the single screw position
        should use the average value of the two corrections from this function.
        Parameters:
            path_delta_vert_1: float, measured difference between the path measured and
                               the 'nominal' path for the vertical mirror and
                               collimator/retro-reflector set 1
            path_delta_vert_2: float, measured difference between the path measured and
                               the 'nominal' path for the vertical mirror and
                               collimator/retro-reflector set 2
            path_delta_horiz_1: float, measured difference between the path measured and
                                the 'nominal' path for the horizontal mirror and
                                collimator/retro-reflector set 1
            path_delta_horiz_2: float, measured difference between the path measured and
                                the 'nominal' path for the horizontal mirror and
                                collimator/retro-reflector set 2
        Returns:
            tuple[float, float, float, float], the required adjustments for the mirrors,
            two for the vertical and two for the horizontal mirrors (vert_1, vert_2,
            horiz_1, horiz_2) to align the mirror
        """
        # The path can be approximated by the hypotenuse of a right triangle, which is
        # equal to the adjacent length divided by the cosine of the angle. Since the
        # laser hits the mirror and is reflected back, this is twice
        # the path, so to get the correction we just divide this by two.

        # approximate offset based on reflection angle at center
        # maximum deviation is <1% over full ellipse range
        horiz_cosine = np.cos(np.radians(self.inter_to_retro_horiz_angle) / 2.0)
        dpos_v1 = path_delta_vert_1 / (2.0 * horiz_cosine)
        dpos_v2 = path_delta_vert_2 / (2.0 * horiz_cosine)
        # The diagonal beam path is dominated by the 45° angle in vertical
        # plane, horizontal deviation is thus ignored. But both mirrors
        # have influence on measured length.
        vert_cosine = (
            np.sqrt(2) / 2.0
        )  # The angle is 45 degrees, so use exact value, rather than calculated cosine
        screw_adjustment_horiz_1 = (
            path_delta_horiz_1 / (2.0 * vert_cosine) - (dpos_v1 + dpos_v2) / 2.0
        )
        screw_adjustment_horiz_2 = (
            path_delta_horiz_2 / (2.0 * vert_cosine) - (dpos_v1 + dpos_v2) / 2.0
        )
        # TODO: include the location of the screws in the horizontal calculation
        c2_z = 40.0
        c1_z = 80.0
        s2_z = 17.5
        s1_z = 123.5
        dd_v = (dpos_v2 - dpos_v1) / (c2_z - c1_z)
        screw_adjustment_vert_1 = (s1_z - c1_z) * dd_v + dpos_v1
        screw_adjustment_vert_2 = (s2_z - c1_z) * dd_v + dpos_v1
        return (
            screw_adjustment_vert_1,
            screw_adjustment_vert_2,
            screw_adjustment_horiz_1,
            screw_adjustment_horiz_2,
        )


class CalcTester(TestCase):
    calc: SeleneCalculator

    def setUp(self):
        self.calc = SeleneCalculator()

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
        class Bla:
            debug = print

        log = Bla()
        self.calc.log = log
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
