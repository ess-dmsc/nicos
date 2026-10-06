import numpy as np

# References
# Distribution: https://www.sciencedirect.com/science/article/abs/pii/S0921452604011792
# Reolution to Slit:https://docs.mantidproject.org/nightly/algorithms/CalculateSlits-v1.html

# Simplified from (2*sqrt(2*log(2))) * (1/(2*sqrt(3)))
DISTRIBUTION = np.sqrt((2 * np.log(2)) / 3)


def resolution_to_slit(l2, l12, ia, res, footprint):
    sinTheta = (footprint / 1000) * (np.sin(np.radians(ia)))
    slitDeltaTheta = np.radians(ia * res)

    slit2 = sinTheta - (2 * l2 * np.tan(slitDeltaTheta))
    slit1 = (2 * l12 * np.tan(slitDeltaTheta)) - slit2
    slit2 = float(slit2 * 1000)
    slit1 = float(slit1 * 1000)

    return [slit1, slit2]


def slit_to_resoultion(l2, l12, ia, slit1, slit2):
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
        float(DISTRIBUTION / (l12 * np.radians(ia)) * np.sqrt((slit1**2) + (slit2**2)))
        * 100
    )

    return [penumbra, umbra, slitDeltaTheta, sinTheta]
