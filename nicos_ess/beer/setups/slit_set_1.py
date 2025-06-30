description = "Slit set 1"

group = "optional"

slit_1_mode_map = {
    "0 - 40, 80": (40, 80),
    "1 - 40, 80": (40, 80),
    "2 - 40, 80": (40, 80),
    "3 - 40, 80": (40, 80),
    "4 - 40, 80": (40, 80),
    "5 - 35, 80": (35, 80),
    "6 - 20, 80": (20, 80),
    "7 - 40, 80": (40, 80),
    "8 - 40, 80": (40, 80),
    "9 - 35, 80": (35, 80),
    "10 - 12, 80": (12, 80),
    "11 - 10, 10": (10, 10),
    "12 - 10, 10": (10, 10),
    "13 - 20, 20": (20, 20),
    "14 - 40, 40": (40, 40),
    "15 - 40, 40": (40, 40),
    "16 - 12, 80": (12, 80),
}


def _position_left(map: dict[str, tuple[int, int]]) -> float:
    return -map["0 - 40, 80"][0] / 2


def _position_right(map: dict[str, tuple[int, int]]) -> float:
    return map["0 - 40, 80"][0] / 2


def _position_up(map: dict[str, tuple[int, int]]) -> float:
    return map["0 - 40, 80"][1] / 2


def _position_down(map: dict[str, tuple[int, int]]) -> float:
    return -map["0 - 40, 80"][1] / 2


devices = dict(
    slit_1_u=device(
        "nicos.devices.generic.VirtualMotor",
        description="Upper edge of slit set",
        fmtstr="%.2f",
        unit="mm",
        speed=0.5,
        abslimits=(5, 40),
        target=_position_up(slit_1_mode_map),
        visibility=(),
    ),
    slit_1_b=device(
        "nicos.devices.generic.VirtualMotor",
        description="Bottom edge of slit set",
        fmtstr="%.2f",
        unit="mm",
        speed=0.5,
        abslimits=(-40, -5),
        target=_position_down(slit_1_mode_map),
        visibility=(),
    ),
    slit_1_l=device(
        "nicos.devices.generic.VirtualMotor",
        description="Left edge of slit set",
        fmtstr="%.2f",
        unit="mm",
        speed=0.5,
        abslimits=(-20, -5),
        target=_position_left(slit_1_mode_map),
        visibility=(),
    ),
    slit_1_r=device(
        "nicos.devices.generic.VirtualMotor",
        description="Right edge of slit set",
        fmtstr="%.2f",
        unit="mm",
        speed=0.5,
        abslimits=(5, 20),
        target=_position_right(slit_1_mode_map),
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
        "nicos_ess.devices.mapped_controller.MappedController",
        controlled_device="slit_1",
        mapping=slit_1_mode_map,
    ),
)
