description = "The livedata interface for tbl."

excludes = ["just_bin_it"]

devices = dict(
    monitor_1=device(
        "nicos_ess.devices.datasources.livedata.DataChannel",
        description="Accumulated counts of beam monitor 1",
        unit="ADC counts",
        counts=False,
        device_name="monitor_1_histogram",
        source_name="monitor_1",
        workflow_id="tbl/monitor_histogram/1",
        type="monitor",
    ),
    timepix3=device(
        "nicos_ess.devices.datasources.livedata.DataChannel",
        description="Accumulated counts of the Timepix3",
        unit="counts",
        device_name="timepix3_detector_image",
        source_name="timepix3_detector",
        workflow_id="tbl/tbl_detector_timepix3/1",
        type="counter",
    ),
    multiblade=device(
        "nicos_ess.devices.datasources.livedata.DataChannel",
        description="Accumulated counts of the Multi-Blade",
        unit="counts",
        device_name="multiblade_detector_image",
        source_name="multiblade_detector",
        workflow_id="tbl/multiblade_detector_view/1",
        type="counter",
    ),
    he3_bank_0=device(
        "nicos_ess.devices.datasources.livedata.DataChannel",
        description="Accumulated counts of He-3 bank 0",
        unit="counts",
        device_name="he3_detector_bank0_image",
        source_name="he3_detector_bank0",
        workflow_id="tbl/he3_detector_view/1",
        type="counter",
    ),
    he3_bank_1=device(
        "nicos_ess.devices.datasources.livedata.DataChannel",
        description="Accumulated counts of He-3 bank 1",
        unit="counts",
        device_name="he3_detector_bank1_image",
        source_name="he3_detector_bank1",
        workflow_id="tbl/he3_detector_view/1",
        type="counter",
    ),
    # The nGEM sees every neutron twice, once on each plane. Its "counts_total"
    # counts events, which gives 2 per neutron. The image folds the two planes
    # and weights each pixel by 1/2, so the image sums to neutrons.
    ngem=device(
        "nicos_ess.devices.datasources.livedata.DataChannel",
        description="Accumulated neutrons of the nGEM with both planes folded",
        unit="counts",
        device_name="ngem_detector_image",
        source_name="ngem_detector",
        workflow_id="tbl/ngem_detector_view/1",
        type="counter",
    ),
    livedata_detector=device(
        "nicos_ess.devices.datasources.livedata.LiveDataCollector",
        description="The livedata histogrammer",
        brokers=configdata("config.KAFKA_BROKERS"),
        data_topics=["tbl_livedata_nicos_data"],
        commands_topic="tbl_livedata_commands",
        status_topics=["tbl_livedata_heartbeat"],
        images=[
            "monitor_1",
            "timepix3",
            "multiblade",
            "he3_bank_0",
            "he3_bank_1",
            "ngem",
        ],
        timers=["timer"],
        # counters=["pulse_counter"],  # needs ECDC-6093
    ),
    timer=device(
        "nicos_ess.devices.timer.TimerChannel",
        description="Timer",
        fmtstr="%.2f",
        unit="s",
    ),
    pulse_counter=device(
        "nicos_ess.devices.epics.pulse_counter.PulseCounter",
        description="Proton pulses on target (EVR event 17, NiAcqSt)",
        readpv="TBL-DtCmn:Ctrl-EVR-001:EvtNiAcqStCnt-I",
        fmtstr="%d",
    ),
)
