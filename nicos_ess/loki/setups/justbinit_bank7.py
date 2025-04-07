description = "The just-bin-it histogrammer."

devices = dict(
    bank7_2d_det_image=device(
        "nicos_ess.devices.datasources.just_bin_it.JustBinItImage",
        description="A just-bin-it image channel",
        hist_topic="loki_visualisation",
        data_topic="loki_detector_bank7",
        brokers=configdata("config.KAFKA_BROKERS"),
        unit="evts",
        hist_type="2-D DET",
        det_width=512,
        det_height=560,
        det_range=(2465793, 2752512),
    ),
    bank7_1d_tof_image=device(
        "nicos_ess.devices.datasources.just_bin_it.JustBinItImage",
        description="A just-bin-it image channel",
        hist_topic="loki_visualisation",
        data_topic="loki_detector_bank7",
        brokers=configdata("config.KAFKA_BROKERS"),
        unit="evts",
        hist_type="1-D TOF",
        det_width=512,
        det_height=560,
        det_range=(2465793, 2752512),
        tof_range=(0, 100000000),
    ),
    bank7_det=device(
        "nicos_ess.devices.datasources.just_bin_it.JustBinItDetector",
        description="The just-bin-it histogrammer",
        brokers=configdata("config.KAFKA_BROKERS"),
        unit="",
        event_schema="ev44",
        command_topic="loki_jbi_commands",
        response_topic="loki_jbi_responses",
        statustopic=["loki_jbi_heartbeat"],
        images=["bank7_2d_det_image", "bank7_1d_tof_image"],
        hist_schema="hs01",
    ),
)

startupcode = """
SetDetectors(bank7_det)
"""
