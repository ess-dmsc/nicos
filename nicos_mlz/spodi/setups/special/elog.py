description = "setup for the electronic logbook"
group = "special"

devices = dict(
    LogbookHtml=device("nicos.services.elog.handler.html.Handler"),
    LogbookText=device("nicos.services.elog.handler.text.Handler"),
    Logbook=device(
        "nicos.services.elog.Logbook",
        handlers=["LogbookHtml", "LogbookText"],
        cache="spodictrl.spodi.frm2.tum.de",
    ),
)
