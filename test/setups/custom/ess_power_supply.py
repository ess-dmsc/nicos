includes = ["stdsystem"]

devices = dict(
    ps_bank_hv=device(
        "test.nicos_ess.test_devices.doubles.power_supply.FakeCaenSyx527ChannelGroup",
        sources={"module01": "TEST"},
    ),
)
