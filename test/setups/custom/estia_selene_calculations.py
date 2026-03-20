includes = ["stdsystem"]

devices = dict(
    selene_calculator=device(
        "test.nicos_ess.estia.test_selene_calculations.FakeSeleneCalculator",
        description="The device needs a setup",
    )
)