description = (
    "The high and low voltage power supplies for the TBL detector and beam monitors."
)

pv_root = "TBL-DtCmn:PwrC"

# Define board/channel info
hv_sources = [
    {
        "id": "HVM",
        "boards": ["100"],
        "channels": [f"{ch:02}" for ch in range(4)],
        "board_type": "A7030DP",
    },
]


def generate_pvs(sources, prefix):
    pvs = {}
    for source in sources:
        for board in source["boards"]:
            for channel in source["channels"]:
                key = f"{prefix}_{board}_Ch{channel}"
                pvs[key] = {
                    "board_type": source["board_type"],
                    "pv": f"{pv_root}-{source['id']}-{board}:Ch{channel}",
                }
    return pvs


def add_devices(pvs, prefix):
    for key, dev_info in pvs.items():
        pv_prefix = dev_info["pv"]
        board_type = dev_info["board_type"]
        # Read-only devices
        devices[f"{key}_voltage"] = device(
            "nicos_ess.devices.epics.pva.EpicsReadable",
            description=f"Detector {prefix} {board_type} module {key} read voltage",
            readpv=f"{pv_prefix}-VMon",
        )
        devices[f"{key}_leak_current"] = device(
            "nicos_ess.devices.epics.pva.EpicsReadable",
            description=f"Detector {prefix} {board_type} module {key} current",
            readpv=f"{pv_prefix}-IMon",
        )
        devices[f"{key}_enabled"] = device(
            "nicos_ess.devices.epics.pva.EpicsMappedReadable",
            description=f"Detector {prefix} {board_type} module {key} power on/off",
            readpv=f"{pv_prefix}-Status-ON",
        )
        # Admin write devices
        devices[f"{key}_voltage_setpoint"] = device(
            "nicos_ess.devices.epics.pva.EpicsAnalogMoveable",
            description=f"Detector {prefix} {board_type} module {key} set voltage",
            readpv=f"{pv_prefix}-VMon",
            writepv=f"{pv_prefix}-V0Set",
            visibility=(),
            requires={"level": "admin"},
        )
        devices[f"{key}_enabled"] = device(
            "nicos_ess.devices.epics.pva.EpicsMappedMoveable",
            description=f"Detector {prefix} {board_type} module {key} power on/off",
            readpv=f"{pv_prefix}-Status-ON",
            writepv=f"{pv_prefix}-Pw",
            visibility=(),
            requires={"level": "admin"},
        )


# Main setup
hv_pvs = generate_pvs(hv_sources, "mb")

devices = {}
add_devices(hv_pvs, "HV")
