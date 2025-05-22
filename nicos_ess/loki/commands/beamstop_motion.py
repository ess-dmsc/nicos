from nicos.commands import usercommand


@usercommand
def ParkAllArms():
    pass

    # Verify Z1 is in the out-of-beam “park” position above the detector panel, if not Move Z1 to “park” position
    # Verify Z2 is in the out-of-beam “park” position above the detector panel, if not Move Z2 to “park” position
    # Verify Z3 is in the out-of-beam “park” position above the detector panel, if not Move Z3 to “park” position
    # Verify Z4 is in the out-of-beam “park” position above the detector panel, if not Move Z4 to “park” position
    # Verify Z5 is in the out-of-beam “park” position above the detector panel, if not Move Z5 to “park” position

    # beamstop_park_positions = {
    #     "detector_beamstop_z1": 0,
    #     "detector_beamstop_z2": 0,
    #     "detector_beamstop_z3": 0,
    #     "detector_beamstop_z4": 0,
    #     "detector_beamstop_z5": 0,
    # }
    #
    # parking_order = [
    #     "detector_beamstop_z1",
    #     "detector_beamstop_z2",
    #     "detector_beamstop_z3",
    #     "detector_beamstop_z4",
    #     "detector_beamstop_z5",
    # ]
    #
    # for beamstop_arm in parking_order:
    #     beamstop_device = session.getDevice(beamstop_arm)
    #     park_pos = beamstop_park_positions[beamstop_device.name]
    #     beamstop_device.maw(park_pos)
    #     sleep(5)
