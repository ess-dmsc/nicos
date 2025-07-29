# ruff: noqa: F821
description = "JustBinIt histogrammer."

devices = dict(
    det_image=device(
        "nicos_ess.devices.datasources.just_bin_it.JustBinItImage",
        description="A just-bin-it image channel",
        hist_topic="estia_visualisation",
        data_topic="estia_detector",
        brokers=configdata("config.KAFKA_BROKERS"),
        source="just-bin-it",
        unit="evts",
        hist_type="2-D TOF",
        det_range=(0, 10000),
    ),
    det=device(
        "nicos_ess.devices.datasources.just_bin_it.JustBinItDetector",
        description="Just Bin it histogrammer",
        brokers=configdata("config.KAFKA_BROKERS"),
        unit="",
        event_schema="ev44",
        command_topic="estia_jbi_commands",
        response_topic="estia_jbi_responses",
        statustopic=["estia_jbi_heartbeat"],
        images=["det_image"],
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
