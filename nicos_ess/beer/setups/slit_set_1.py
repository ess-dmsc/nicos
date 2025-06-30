description = "Slit set 1"

group = "optional"

slit_1_mode_map = {
    "Mode:0 - Width: 40, Height: 80": [40.0, 80.0],
    "Mode:1 - Width: 40, Height: 80": [40.0, 80.0],
    "Mode:2 - Width: 40, Height: 80": [40.0, 80.0],
    "Mode:3 - Width: 40, Height: 80": [40.0, 80.0],
    "Mode:4 - Width: 40, Height: 80": [40.0, 80.0],
    "Mode:5 - Width: 35, Height: 80": [35.0, 80.0],
    "Mode:6 - Width: 20, Height: 80": [20.0, 80.0],
    "Mode:7 - Width: 40, Height: 80": [40.0, 80.0],
    "Mode:8 - Width: 40, Height: 80": [40.0, 80.0],
    "Mode:9 - Width: 35, Height: 80": [35.0, 80.0],
    "Mode:10 - Width: 12, Height: 80": [12.0, 80.0],
    "Mode:11 - Width: 10, Height: 10": [10.0, 10.0],
    "Mode:12 - Width: 10, Height: 10": [10.0, 10.0],
    "Mode:13 - Width: 20, Height: 20": [20.0, 20.0],
    "Mode:14 - Width: 40, Height: 40": [40.0, 40.0],
    "Mode:15 - Width: 40, Height: 40": [40.0, 40.0],
    "Mode:16 - Width: 12, Height: 80": [12.0, 80.0],
}


def _initial_position_left(map: dict[str, list[float]]) -> float:
    return -map["Mode:0 - Width: 40, Height: 80"][0] / 2


def _initial_position_right(map: dict[str, list[float]]) -> float:
    return map["Mode:0 - Width: 40, Height: 80"][0] / 2


def _initial_position_up(map: dict[str, list[float]]) -> float:
    return map["Mode:0 - Width: 40, Height: 80"][1] / 2


def _initial_position_down(map: dict[str, list[float]]) -> float:
    return -map["Mode:0 - Width: 40, Height: 80"][1] / 2


devices = dict(
    slit_1_u=device(
        "nicos.devices.generic.VirtualMotor",
        description="Upper edge of slit set",
        fmtstr="%.2f",
        unit="mm",
        speed=0.5,
        abslimits=(5, 40),
        target=_initial_position_up(slit_1_mode_map),
        visibility=(),
    ),
    slit_1_b=device(
        "nicos.devices.generic.VirtualMotor",
        description="Bottom edge of slit set",
        fmtstr="%.2f",
        unit="mm",
        speed=0.5,
        abslimits=(-40, -5),
        target=_initial_position_down(slit_1_mode_map),
        visibility=(),
    ),
    slit_1_l=device(
        "nicos.devices.generic.VirtualMotor",
        description="Left edge of slit set",
        fmtstr="%.2f",
        unit="mm",
        speed=0.5,
        abslimits=(-20, -5),
        target=_initial_position_left(slit_1_mode_map),
        visibility=(),
    ),
    slit_1_r=device(
        "nicos.devices.generic.VirtualMotor",
        description="Right edge of slit set",
        fmtstr="%.2f",
        unit="mm",
        speed=0.5,
        abslimits=(5, 20),
        target=_initial_position_right(slit_1_mode_map),
        visibility=(),
    ),
    slit_1=device(
        "nicos.devices.generic.Slit",
        description="Slit set with 4 blades",
        left="slit_1_l",
        right="slit_1_r",
        bottom="slit_1_b",
        top="slit_1_u",
        opmode="centered",
    ),
    config_set=device(
        "nicos_ess.beer.devices.slit_mapped_controller.CenteredSlitMappedController",
        controlled_device="slit_1",
        mapping=slit_1_mode_map,
    ),
)
