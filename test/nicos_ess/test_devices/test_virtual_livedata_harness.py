from nicos.core.constants import FINAL
from nicos_ess.devices.virtual import livedata
from test.nicos_ess.test_devices.doubles import wait_for, wait_until_complete


TOF_WORKFLOW = "dummy/detector_data/panel_0_tof/1@panel_0"
XY_WORKFLOW = "dummy/detector_data/panel_0_xy/1@panel_0"


def create_channel(daemon_device_harness, name, selector):
    return daemon_device_harness.create_master(
        livedata.DataChannel,
        name=name,
        selector=selector,
        type="counter",
    )


def create_collector(daemon_device_harness, counters):
    daemon_device_harness.session.updateLiveData = lambda *args, **kwargs: None
    return daemon_device_harness.create_master(
        livedata.LiveDataCollector,
        name="sim_livedata_detector",
        brokers=["localhost:9092"],
        data_topics=["sim_livedata"],
        status_topics=["sim_livedata_status"],
        responses_topics=["sim_livedata_responses"],
        commands_topic="sim_livedata_commands",
        counters=counters,
    )


class TestVirtualDataChannelHarness:
    def test_daemon_and_poller_share_channel_state_via_cache(self, device_harness):
        daemon_channel, poller_channel = device_harness.create_pair(
            livedata.DataChannel,
            name="livedata_current",
            shared={
                "selector": f"{TOF_WORKFLOW}/current",
                "type": "counter",
            },
        )
        daemon_detector, poller_detector = device_harness.create_pair(
            livedata.LiveDataCollector,
            name="sim_livedata_detector",
            shared={
                "brokers": ["localhost:9092"],
                "data_topics": ["sim_livedata"],
                "status_topics": ["sim_livedata_status"],
                "responses_topics": ["sim_livedata_responses"],
                "commands_topic": "sim_livedata_commands",
                "counters": ["livedata_current"],
            },
        )

        assert device_harness.run_poller(poller_detector.get_current_mapping) == (
            device_harness.run_daemon(daemon_detector.get_current_mapping)
        )

        device_harness.run_daemon(daemon_detector.setPreset, n=1)
        device_harness.run_daemon(daemon_detector.prepare)
        device_harness.run_daemon(daemon_detector.start)
        device_harness.run_daemon(wait_until_complete, daemon_detector, timeout=3.0)
        device_harness.run_daemon(daemon_detector.finish)

        daemon_total = device_harness.run_daemon(lambda: daemon_channel.read()[0])
        wait_for(
            lambda: device_harness.run_poller(lambda: poller_channel.read()[0])
            == daemon_total,
            timeout=2.0,
        )

        assert device_harness.run_poller(lambda: poller_channel.read()[0]) == daemon_total


class TestVirtualLiveDataCollectorHarness:
    def test_seeded_mapping_exposes_current_and_cumulative_outputs(
        self, daemon_device_harness
    ):
        current = create_channel(
            daemon_device_harness,
            "livedata_current",
            f"{TOF_WORKFLOW}/current",
        )
        cumulative = create_channel(
            daemon_device_harness,
            "livedata_cumulative",
            f"{TOF_WORKFLOW}/cumulative",
        )
        collector = create_collector(
            daemon_device_harness,
            [current.name, cumulative.name],
        )

        mapping = collector.get_current_mapping()

        assert len(mapping) == 2
        assert any(selector.endswith("/current") for selector in mapping.values())
        assert any(selector.endswith("/cumulative") for selector in mapping.values())

    def test_scalar_preset_completes_using_local_da00_generation(
        self, daemon_device_harness
    ):
        current = create_channel(
            daemon_device_harness,
            "livedata_current",
            f"{TOF_WORKFLOW}/current",
        )
        cumulative = create_channel(
            daemon_device_harness,
            "livedata_cumulative",
            f"{TOF_WORKFLOW}/cumulative",
        )
        collector = create_collector(
            daemon_device_harness,
            [current.name, cumulative.name],
        )

        collector.setPreset(n=1)
        collector.prepare()
        collector.start()
        wait_until_complete(collector, timeout=3.0)
        collector.finish()
        scalars, arrays = collector.readResults(FINAL)

        assert collector.isCompleted() is True
        assert arrays == []
        assert scalars[0] >= 1
        assert current.read()[0] >= 1
        assert cumulative.read()[0] >= current.read()[0]

    def test_workflow_config_updates_shape_while_running(
        self, daemon_device_harness
    ):
        channel = create_channel(
            daemon_device_harness,
            "livedata_tof",
            f"{TOF_WORKFLOW}/current",
        )
        collector = create_collector(daemon_device_harness, [channel.name])

        collector.setPreset(n=1)
        collector.prepare()
        collector.start()
        wait_for(lambda: channel.read()[0] > 0, timeout=2.0)

        assert channel.arrayInfo()[0].shape == (128,)

        collector.send_workflow_config(
            key_source="panel_0",
            config_json={"params": {"time_of_arrival_bins": 32}},
        )
        wait_for(lambda: channel.arrayInfo()[0].shape == (32,), timeout=2.0)
        collector.stop()

        assert channel.arrayInfo()[0].shape == (32,)

    def test_remove_job_updates_mapping(
        self, daemon_device_harness
    ):
        current = create_channel(
            daemon_device_harness,
            "livedata_current",
            f"{XY_WORKFLOW}/current",
        )
        cumulative = create_channel(
            daemon_device_harness,
            "livedata_cumulative",
            f"{XY_WORKFLOW}/cumulative",
        )
        collector = create_collector(
            daemon_device_harness,
            [current.name, cumulative.name],
        )
        job = collector._registry.resolve_latest(
            "dummy/detector_data/panel_0_xy/1",
            "panel_0",
        )

        assert job is not None
        assert collector.get_current_mapping()

        collector.send_job_command(
            job_id={
                "source_name": job.source_name,
                "job_number": job.job_number,
            },
            action="remove",
        )
        wait_for(lambda: collector.get_current_mapping() == {}, timeout=2.0)

        assert collector.get_current_mapping() == {}
