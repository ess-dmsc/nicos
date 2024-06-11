import pytest
from nicos_ess.devices.epics.area_detector import AreaDetector
from test.unit_tests.class_factory.class_factory import (
    test_factory,
    _initParam,
    base_init,
    base_setattr,
    init,
)


@pytest.fixture()
def area_detector():
    method_overrides = {
        "__init__": base_init,
        "__setattr__": base_setattr,
        "init": init,
        "_initParam": _initParam,
    }

    TestAreaDetector = test_factory(AreaDetector, method_overrides)

    test_ad = TestAreaDetector(
        name="orca_camera",
        description="The light tomography Orca camera.",
        pv_root="Orca:cam1:",
        ad_kafka_plugin="orca_kafka_plugin",
        image_topic="nido_camera",
        unit="images",
        brokers=["localhost:9092"],
        pollinterval=None,
        pva=True,
        monitor=True,
    )
    return test_ad


def test_can_init_device(area_detector):
    assert area_detector is not None
    assert area_detector.name == "orca_camera"
    assert area_detector.description == "The light tomography Orca camera."
    assert area_detector.pv_root == "Orca:cam1:"
    assert not hasattr(
        area_detector, "ad_kafka_plugin"
    )  # does not create attached devices
    assert area_detector.image_topic == "nido_camera"
    assert area_detector.unit == "images"
    assert area_detector.brokers == ["localhost:9092"]
    assert area_detector.pollinterval is None
    assert area_detector.pva is True
    assert area_detector.monitor is True
