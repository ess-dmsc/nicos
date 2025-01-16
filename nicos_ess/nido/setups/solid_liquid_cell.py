description = "The solid liquid cells for ESTIA"

pv_root = "SE:SE-BV:"

devices = dict()

num_cells = 7
for i in range(1, num_cells + 1):
    devices[f"cell_{i}"] = device(
        "nicos_ess.estia.devices.solid_liquid_cell.SolidLiquidCell",
        description=f"The solid liquid cell {i}.",
        top_s1=f"cell_{i}_top_s1",
        top_s2=f"cell_{i}_top_s2",
        top_s3=f"cell_{i}_top_s3",
        bottom_s1=f"cell_{i}_bottom_s1",
        bottom_s2=f"cell_{i}_bottom_s2",
        bottom_s3=f"cell_{i}_bottom_s3",
        temperature=f"cell_{i}_temperature",
    )

    for j in range(1, 4):
        devices[f"cell_{i}_top_s{j}"] = device(
            "nicos_ess.devices.epics.pva.EpicsMappedMoveable",
            description=f"Top side solenoid {j} of cell {i}.",
            readpv=f"{pv_root}Cell{i}TopS{j}-R",
            writepv=f"{pv_root}Cell{i}TopS{j}-S",
            visibility=(),
        )
        devices[f"cell_{i}_bottom_s{j}"] = device(
            "nicos_ess.devices.epics.pva.EpicsMappedMoveable",
            description=f"Bottom side solenoid {j} of cell {i}.",
            readpv=f"{pv_root}Cell{i}BotS{j}-R",
            writepv=f"{pv_root}Cell{i}BotS{j}-S",
            visibility=(),
        )
        devices[f"cell_{i}_temperature"] = device(
            "nicos_ess.devices.epics.pva.EpicsReadable",
            description=f"Temperature sensor of cell {i}.",
            readpv=f"{pv_root}TCell{i}-R",
            visibility=(),
        )
