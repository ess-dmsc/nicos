description = "W&T Box * 4-20mA * Nr. 1"

includes = []
_wutbox = "wut-4-20-01"
_wutbox_dev = _wutbox.replace("-", "_")

devices = {
    _wutbox_dev + "_1": device(
        "nicos_mlz.sans1.devices.wut.WutReadValue",
        hostname=_wutbox + ".sans1.frm2.tum.de",
        port=1,
        description="input 1 current",
        fmtstr="%.3F",
        loglevel="info",
        pollinterval=5,
        maxage=20,
        unit="A",
    ),
    _wutbox_dev + "_2": device(
        "nicos_mlz.sans1.devices.wut.WutReadValue",
        hostname=_wutbox + ".sans1.frm2.tum.de",
        port=2,
        description="input 2 current",
        fmtstr="%.3F",
        loglevel="info",
        pollinterval=5,
        maxage=20,
        unit="A",
    ),
}
