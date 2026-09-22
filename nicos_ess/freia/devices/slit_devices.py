import numpy as np

from nicos.core import (
    DeviceMixinBase,
    Override,
)

# FROM (2*np.sqrt(2*np.log(2))) * (1/(2*np.sqrt(3))) on the Colimation Spreadsheet
DISTRIBUTION = np.sqrt((2 * np.log(2)) / 3)


class ColimationCalculator(DeviceMixinBase):
    """Functions for calculating the resolution and gap for colimation slits"""

    parameter_overrides = {
        "fmtstr": Override(default=""),
        "unit": Override(default="", mandatory=False, settable=False),
    }

    def resolution_to_slit(self, l2, l12, ia, res, footprint):
        sinTheta = (footprint / 1000) * (np.sin(np.radians(ia)))
        slitDeltaTheta = np.radians(ia * res)

        slit2 = sinTheta - (2 * l2 * np.tan(slitDeltaTheta))
        slit1 = (2 * l12 * np.tan(slitDeltaTheta)) - slit2
        slit2 = float(slit2 * 1000)
        slit1 = float(slit1 * 1000)

        return [slit1, slit2]

    def slit_to_resoultion(self, l2, l12, ia, slit1, slit2):
        slit1 = slit1 / 1000
        slit2 = slit2 / 1000
        dist_ratio = l2 / l12
        beam_height = slit2 + (dist_ratio) * (slit1 + slit2)

        penumbra = float((beam_height / np.sin(np.deg2rad(ia))) * 1000)
        umbra = float((slit2 * 1000) / (np.sin(np.radians(ia))))

        slitDeltaTheta = (
            float(np.rad2deg(np.arctan((slit1 + slit2) / (2 * l12))) / ia) * 100
        )
        sinTheta = (
            float(
                DISTRIBUTION / (l12 * np.radians(ia)) * np.sqrt((slit1**2) + (slit2**2))
            )
            * 100
        )

        return penumbra, umbra, slitDeltaTheta, sinTheta


class KineticSlits(DeviceMixinBase):
    def kinetic_gap_review():
        return
