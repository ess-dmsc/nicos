description = "The just-bin-it histogrammer."

devices = dict(
    det_image1=device(
        "nicos_ess.devices.datasources.just_bin_it.JustBinItImage",
        description="A just-bin-it image channel",
        hist_topic="bifrost_visualisation",
        data_topic="bifrost_detector",
        brokers=configdata("config.KAFKA_BROKERS"),
        unit="evts",
        hist_type="2-D DET",
        det_width=900,
        det_height=15,
        det_range=(1, 13500),
    ),
    det_image2=device(
        "nicos_ess.devices.datasources.just_bin_it.JustBinItImage",
        description="A just-bin-it image channel",
        hist_topic="bifrost_visualisation",
        data_topic="bifrost_detector",
        brokers=configdata("config.KAFKA_BROKERS"),
        unit="evts",
        hist_type="2-D TOF",
        det_width=900,
        det_height=15,
        det_range=(1, 13500),
        tof_range=(0, 1000000),
    ),
    det=device(
        "nicos_ess.devices.datasources.just_bin_it.JustBinItDetector",
        description="The just-bin-it histogrammer",
        brokers=configdata("config.KAFKA_BROKERS"),
        unit="",
        command_topic="bifrost_jbi_commands",
        response_topic="bifrost_jbi_responses",
        statustopic="bifrost_jbi_heartbeat",
        images=["det_image1", "det_image2"],
        hist_schema="hs01",
        event_schema="ev44",
    ),
)

startupcode = """
SetDetectors(det)
"""
