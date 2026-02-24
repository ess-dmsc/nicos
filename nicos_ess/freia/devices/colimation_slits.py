import numpy as np

from nicos.core import (
    Attach,
    Moveable,
    Override,
    Param,
    Readable,
    Value,
    dictof,
    multiStatus,
    oneof,
    status,
    tupleof,
)

# FROM (2*np.sqrt(2*np.log(2))) * (1/(2*np.sqrt(3))) on the Colimation Spreadsheet
# https://www.sciencedirect.com/science/article/pii/S0921452604011792?pes=vor&utm_source=scopus&getft_integrator=scopus
DISTRIBUTION = np.sqrt((2 * np.log(2)) / 3)


class ColimationCalculator(Readable):
    """Functions for calculating the resolution and gap for colimation slits"""

    parameter_overrides = {
        "fmtstr": Override(default="L2s, L12, IA, res, footprint, slit1, slit 2"),
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


class ColimationSlits(ColimationCalculator, Moveable):
    parameters = {
        "opmode": Param(
            "Mode of operation",
            type=oneof("res_to_slit", "slit_to_res"),
            settable=True,
            default="res_to_slit",
        )
    }
    valuetype = tupleof(float, float, float, float, float)

    def doStart(self, target):
        pass

    def _doReadPositions(self, maxage):
        pass

    def doRead(self, maxage=0):
        return self._doReadPositions(maxage)

    def doStatus(self, maxage=0):
        return status.OK, ""

    def doSetPosition(self, pos):
        pass

    def valueInfo(self):
        if self.opmode == "res_to_slit":
            return (
                Value("L2s", unit="m", fmtstr="%.3f"),
                Value("L12", unit="m", fmtstr="%.3f"),
                Value("Incident Angle", unit="deg", fmtstr="%.3f"),
                Value("Slit Delta Theta", unit="mm", fmtstr="%.3f"),
                Value("Footprint", unit="deg", fmtstr="%.3f"),
            )
        else:
            return (
                Value("L2s", unit="m", fmtstr="%.3f"),
                Value("L12", unit="m", fmtstr="%.3f"),
                Value("Incident Angle", unit="deg", fmtstr="%.3f"),
                Value("Slit 1", unit="mm", fmtstr="%.3f"),
                Value("Slit 2", unit="mm", fmtstr="%.3f"),
            )
