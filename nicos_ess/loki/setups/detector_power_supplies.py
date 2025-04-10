description = "The high and low voltage power supplies for the LoKI detector."

pv_root = "LOKI-DtCmn:PwrC"

hv_info = {
    "id": "HVM",
    "boards": ["100", "101", "102", "105", "106"],
    "channels": [f"{ch:>02}" for ch in range(0, 12)],
}

lv_info = {
    "id": "LVM",
    "boards": [str(board) for board in range(107, 116)],
    "channels": [f"{ch:>02}" for ch in range(0, 8)],
}

hv_pvs = {}
for board in hv_info["boards"]:
    for channel in hv_info["channels"]:
        key = f"HV_{board}_Ch{channel}"
        val = f"{pv_root}-{hv_info['id']}-{board}:Ch{channel}"
        hv_pvs[key] = val

lv_pvs = {}
for board in lv_info["boards"]:
    for channel in lv_info["channels"]:
        key = f"LV_{board}_Ch{channel}"
        val = f"{pv_root}-{lv_info['id']}-{board}:Ch{channel}"
        lv_pvs[key] = val


devices = dict()

for key, val in hv_pvs.items():
    devices[f"{key}_voltage"] = device(
        "nicos_ess.devices.epics.pva.EpicsReadable",
        description=f"Detector HV A7030DP module {key} voltage",
        readpv=f"{val}-VMon",
        visibility=(),
    )

for key, val in hv_pvs.items():
    devices[f"{key}_current"] = device(
        "nicos_ess.devices.epics.pva.EpicsReadable",
        description=f"Detector HV A7030DP module {key} current",
        readpv=f"{val}-IMon",
        visibility=(),
    )

for key, val in lv_pvs.items():
    devices[f"{key}_voltage"] = device(
        "nicos_ess.devices.epics.pva.EpicsReadable",
        description=f"Detector LV A2552 module {key} voltage",
        readpv=f"{val}-VMon",
        visibility=(),
    )

for key, val in lv_pvs.items():
    devices[f"{key}_current"] = device(
        "nicos_ess.devices.epics.pva.EpicsReadable",
        description=f"Detector LV A2552 module {key} current",
        readpv=f"{val}-IMon",
        visibility=(),
    )
