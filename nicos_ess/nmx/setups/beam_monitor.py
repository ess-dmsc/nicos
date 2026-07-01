description = "NMX beam monitor actuator"

pv_root = "NMX-BM2:MC-Pne-01:"

# TODO: Use mapped or epics shutter?
devices = dict(
    beam_monitor=device(
        "nicos_ess.devices.epics.pva.shutter.EpicsShutter",
        description="Beam monitor actuator",
        writepv=f"{pv_root}ShtOpen",
        readpv=f"{pv_root}ShtAuxBits07",
        resetpv=f"{pv_root}ShtErrRst",
        msgtxt=f"{pv_root}ShtMsgTxt",
    ),
    beam_monitor__status=device(
        "nicos_ess.devices.epics.pva.EpicsMappedReadable",
        description="Beam monitor actuator status",
        readpv=f"{pv_root}ShtAuxBits07",
        pva=True,
        monitor=True,
        pollinterval=0.5,
        maxage=None,
        visibility={},
    ),
    beam_monitor__control=device(
        "nicos_ess.devices.epics.pva.EpicsMappedMoveable",
        description="Beam monitor actuator control",
        readpv=f"{pv_root}ShtOpen",
        writepv=f"{pv_root}ShtOpen",
        pva=True,
        monitor=True,
        pollinterval=0.5,
        maxage=None,
        visibility={},
    ),
)
