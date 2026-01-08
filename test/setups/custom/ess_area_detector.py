includes = ["stdsystem"]

devices = dict(
    ad_1=device(
        "test.nicos_ess.test_devices.test_area_detector.FakeAreaDetector",
        pv_root="TEST",
        image_pv="TEST_IMAGE",
    ),
)
