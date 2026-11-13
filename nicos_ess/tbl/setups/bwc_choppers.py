description = "The bandwidth choppers BWC1 and BWC2, one device per disc"

chic_root = "TBL-ChpSy1:Chop-CHIC-001:"

devices = dict(
    bwc1_chopper=device(
        "nicos_ess.devices.epics.chopper.EssChopper",
        description="Bandwidth chopper 1 (BWC-101)",
        pv_root="TBL-ChpSy1:Chop-BWC-101:",
        chic_root=chic_root,
        legacy_spd_sign=True,
        speeds=[-28, -14, -7, 0, 7, 14, 28],
        slit_edges=[[0.0, 170.0]],
        beam_position=299.3,
        resolver_sign=-1,
        tdc_resolver_position=341.7,
        distance=8.5412,
    ),
    bwc2_chopper=device(
        "nicos_ess.devices.epics.chopper.EssChopper",
        description="Bandwidth chopper 2 (BWC-102)",
        pv_root="TBL-ChpSy1:Chop-BWC-102:",
        chic_root=chic_root,
        legacy_spd_sign=True,
        speeds=[-28, -14, -7, 0, 7, 14, 28],
        slit_edges=[[0.0, 170.0]],
        beam_position=233.5,
        resolver_sign=1,
        tdc_resolver_position=342.5,
        distance=8.5605,
    ),
)
