import numpy as np

DISTRIBUTION = np.sqrt((2 * np.log(2)) / 3)


def resolution_to_slit(l2, l12, ia, res, footprint):
    """The resolution_to_slit function calculates the gap needed by each slit to output the
    desired footprint size on a sample. The original function was developed by the mantId project
    in C: https://docs.mantidproject.org/nightly/algorithms/CalculateSlits-v1.html

     -----INPUT-----
     l2 - distance from the sample to the second set of slits (m)
     l12 - distance between the collimation slits (m)
     ia - the incident angle (deg)
     res - the desired resolution (%)
     footprint - the desired footprint size (mm)

     -----OUTPUT-----
     slit1 - the required gap size for slit1 (mm)
     slit2 - the required gap size for slit2 (mm)
    """

    sinTheta = (footprint / 1000) * (np.sin(np.radians(ia)))
    slitDeltaTheta = np.radians(ia * res)

    slit2 = sinTheta - (2 * l2 * np.tan(slitDeltaTheta))
    slit1 = (2 * l12 * np.tan(slitDeltaTheta)) - slit2
    slit2 = float(slit2 * 1000)
    slit1 = float(slit1 * 1000)

    return [slit1, slit2]


def slit_to_resoultion(l2, l12, ia, slit1, slit2):
    """The slit_to_resolution function calculates the footprint created by a pair of slits
    when the gap each slit creates is known.

    The function requires the use of a constant labelled DISTRIBUTION. Which is based on an equation from
    'On the resolution and intensity of a time-of-flight neutron reflectometer' (van Well et al) in
    section 3 'Resolution' which provides the distribution's full-width at half-maximum as
    (2*sqrt(2*log(2))) * (1/(2*sqrt(3))). Which is then further simplified by the FREIA team to the provided
    DISTRIBUTION constant.

    -----INPUT-----
    l2 - distance from the sample to the second set of slits (m)
    l12 - distance between the collimation slits (m)
    ia - the incident angle (deg)
    slit1 - the gap created by slit1 (mm)
    slit2 - the gap created by slit2 (mm)

    -----OUTPUT-----
    penumbra - the penumbra of the resulting footprint (mm)
    umbra - the umbra of the resulting footprint (mm)
    slitDeltaTheta - Resolution quality in max/simple geometry
    sinTheta - Resulting resolution quality (%)
    """
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
