description = "The mini-chopper for YMIR"

devices = dict(
    mini_chopper=device(
        "nicos_ess.devices.epics.chopper.EssChopper",
        description="The mini-chopper",
        pv_root="YMIR-ChpSy1:Chop-MIC-101:",
        chic_root="YMIR-ChpSy1:Chop-CHIC-001:",
        legacy_spd_sign=True,
        speeds=[-14, -7, 0, 7, 14],
        # Placeholder geometry: the disc is not documented yet.
        slit_edges=[[0.0, 90.0]],
        beam_position=0.0,
    ),
)
