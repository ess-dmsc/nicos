import numpy as np

from nicos.core import (
    Attach,
    Moveable,
    Override,
    Readable,
    Value,
    multiStatus,
    status,
    tupleof,
)

# FROM (2*np.sqrt(2*np.log(2))) * (1/(2*np.sqrt(3))) on the Colimation Spreadsheet
# https://www.sciencedirect.com/science/article/pii/S0921452604011792?pes=vor&utm_source=scopus&getft_integrator=scopus
DISTRIBUTION = np.sqrt((2 * np.log(2)) / 3)


class ColimationCalculator(Readable):
    """Functions for calculating the resolution and gap for colimation slits"""

    def resolution_to_slit(self, l2, l12, ia, res, footprint):
        sinTheta = (footprint / 1000) * (np.sin(np.radians(ia)))
        slitDeltaTheta = np.radians(ia * res)

        slit2 = (sinTheta - (2 * l2 * np.tan(slitDeltaTheta))) * 1000
        slit1 = ((2 * l12 * np.tan(slitDeltaTheta)) - slit2) * 1000

        return [slit1, slit2]

    def slit_to_resoultion(self, l2, l12, ia, slit1, slit2):
        slit1 = slit1 / 1000  # mm to m
        slit2 = slit2 / 1000
        sinTheta = (
            DISTRIBUTION / (l12 * np.radians(ia)) * np.sqrt((slit1 ^ 2) + (slit2 ^ 2))
        )
        slitDeltaTheta = np.rad2deg(np.arctan((slit1 + slit2) / (2 * l12))) / ia

        beam_height = ((slit2 + (l2 / l12)) * (slit1 + slit2)) * 1000
        penumbra = (beam_height / np.sin(np.deg2rad(ia))) * 1000
        umbra = 0
        return [penumbra, umbra, beam_height]


class ColimationSlits(ColimationCalculator, Moveable):
    valuetype = tupleof(float, float, float, float, float)

    def resolution_to_slit(self, l2, l12, ia, res, footprint):
        sinTheta = (footprint / 1000) * (np.sin(np.radians(ia)))
        slitDeltaTheta = np.radians(ia * res)

        slit2 = (sinTheta - (2 * l2 * np.tan(slitDeltaTheta))) * 1000
        slit1 = ((2 * l12 * np.tan(slitDeltaTheta)) - slit2) * 1000

        return [slit1, slit2]

    def slit_to_resoultion(self, l2, l12, ia, slit1, slit2):
        slit1 = slit1 / 1000  # mm to m
        slit2 = slit2 / 1000
        sinTheta = (
            DISTRIBUTION / (l12 * np.radians(ia)) * np.sqrt((slit1 ^ 2) + (slit2 ^ 2))
        )
        slitDeltaTheta = np.rad2deg(np.arctan((slit1 + slit2) / (2 * l12))) / ia

        beam_height = ((slit2 + (l2 / l12)) * (slit1 + slit2)) * 1000
        penumbra = (beam_height / np.sin(np.deg2rad(ia))) * 1000
        umbra = 0
        return [penumbra, umbra, beam_height]

    def _doReadPositions(self, maxage):
        pass

    def doRead(self, maxage=0):
        return self._doReadPositions(maxage)

    def doStatus(self, maxage=0):
        return status.OK, ""

    def doSetPosition(self, pos):
        pass
