devices = dict(
    lakeshore_A=device(
        "test.nicos_ess.estia.test_estia_lakeshore336.FakeEstiaFlowCryo",
        description="Input A of the Flow Cryo",
        pvroot="TEST",
        input_pos="A",
        output_num=1,
    ),
    lakeshore_B=device(
        "test.nicos_ess.estia.test_estia_lakeshore336.FakeEstiaFlowCryo",
        description="Input A of the Flow Cryo",
        pvroot="TEST",
        input_pos="B",
        output_num=2,
    ),
)
