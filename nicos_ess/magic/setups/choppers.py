description = "The MAGIC choppers: PSC1, PSC2, SC1 and BC"

chic_root = "MAGIC-ChpSy1:Chop-CHIC-001:"

devices = dict(
    pulse_shape_chopper_1=device(
        "nicos_ess.devices.epics.chopper.EssChopper",
        description="Pulse shaping chopper 1 (PSC-101)",
        pv_root="MAGIC-ChpSy1:Chop-PSC-101:",
        chic_root=chic_root,
        legacy_spd_sign=True,
        speeds=[-14, -7, 0, 7, 14],
        slit_edges=[[0.0, 105.0], [138.2, 146.8]],
        beam_position=171.0,
        distance=6.229267,
        # The axle is 0.285 m above the beam.
        guide_position="DOWN",
    ),
    pulse_shape_chopper_2=device(
        "nicos_ess.devices.epics.chopper.EssChopper",
        description="Pulse shaping chopper 2 (PSC-102)",
        pv_root="MAGIC-ChpSy1:Chop-PSC-102:",
        chic_root=chic_root,
        legacy_spd_sign=True,
        speeds=[-14, -7, 0, 7, 14],
        slit_edges=[[0.0, 105.0], [318.2, 326.8]],
        beam_position=62.5,
        distance=6.244201,
        # The axle is 0.285 m below the beam.
        guide_position="UP",
    ),
    selection_chopper=device(
        "nicos_ess.devices.epics.chopper.EssChopper",
        description="Selection chopper (SC-101)",
        pv_root="MAGIC-ChpSy1:Chop-SC-101:",
        chic_root=chic_root,
        legacy_spd_sign=True,
        speeds=[-14, -7, 0, 7, 14],
        slit_edges=[[0.0, 20.6]],
        beam_position=258.3,
        distance=6.735001,
    ),
    bandwidth_chopper=device(
        "nicos_ess.devices.epics.chopper.EssChopper",
        description="Bandwidth chopper (BC-201)",
        pv_root="MAGIC-ChpSy1:Chop-BC-201:",
        chic_root=chic_root,
        legacy_spd_sign=True,
        speeds=[-14, -7, 0, 7, 14],
        slit_edges=[[0.0, 180.0]],
        beam_position=0.0,
        distance=79.9,
    ),
)
