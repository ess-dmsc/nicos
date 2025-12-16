includes = ["stdsystem"]

devices = dict(
    ps_channel_1=device(
        "test.nicos_ess.test_devices.test_power_supply.FakePowerSupplyChannel",
        ps_pv="TEST",
        mapping={"OFF": 0, "ON": 1},
    ),
    ps_bank_hv=device(
        "test.nicos_ess.test_devices.test_power_supply.FakePowerSupplyBank",
        ps_channels=["ps_channel_1"],
    ),
)
