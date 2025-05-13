description = "TBL Bee Beans NGEM"

devices = dict(
    vacuum_gauge=device(
        "nicos_ess.devices.epics.pva.EpicsReadable",
        description="Vacuum gauge",
        readpv="TBL-VacBnkr:Vac-VGP-010:PrsR",
        visiblitity=(),
    ),
)