# ruff: noqa: F821
description = "JustBinIt histogrammer."

devices = dict(
    det_image1=device(
        "nicos_ess.devices.datasources.just_bin_it.JustBinItImage",
        description="A just-bin-it image channel",
        hist_topic="hist_topic_1",
        data_topic="estia_detector",
        brokers=configdata("config.KAFKA_BROKERS"),
        source="just-bin-it",
        unit="evts",
        hist_type="2-D TOF",
        det_range=(0, 10000),
    ),
    det_image2=device(
        "nicos_ess.devices.datasources.just_bin_it.JustBinItImage",
        description="A just-bin-it image channel",
        hist_topic="hist_topic_2",
        data_topic="estia_detector",
        brokers=configdata("config.KAFKA_BROKERS"),
        source="just-bin-it",
        unit="evts",
        hist_type="1-D TOF",
        det_range=(0, 10000),
    ),
    det=device(
        "nicos_ess.devices.datasources.just_bin_it.JustBinItDetector",
        description="Just Bin it histogrammer",
        brokers=configdata("config.KAFKA_BROKERS"),
        unit="",
        command_topic="estia_jbi_commands",
        response_topic="estia_jbi_responses",
        statustopic=["estia_jbi_heartbeat"],
        images=["det_image1", "det_image2"],
        hist_schema="hs01",
        timers=["timer"],
    ),
    timer=device(
        "nicos_ess.devices.timer.TimerChannel",
        description="Timer",
        fmtstr="%.2f",
        unit="s",
    ),
)

startupcode = """
SetDetectors(det)
"""
