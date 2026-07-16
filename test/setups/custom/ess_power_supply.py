includes = ["stdsystem"]

devices = dict(
    ps_bank_hv=device(
        "test.nicos_ess.test_devices.test_power_supply.FakePowerSupplyGroup",
        sources={"module01": "TEST"},
    ),
)
