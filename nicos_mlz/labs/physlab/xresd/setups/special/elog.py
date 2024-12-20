description = "setup for the electronic logbook"
group = "special"

devices = dict(
    LogbookHtml=device("nicos.services.elog.handler.html.Handler"),
    LogbookText=device("nicos.services.elog.handler.text.Handler"),
    LogbookWorkbench=device(
        "nicos.services.elog.handler.eworkbench.workbench_rabbit_writer.Handler",
        rabbit_url="localhost",
        rabbit_port=5672,
        rabbit_virtual_host="/",
        rabbit_username="guest",
        rabbit_password="guest",
        rabbit_static_queue="xresd-workbench",
    ),
    Logbook=device(
        "nicos.services.elog.Logbook",
        handlers=["LogbookHtml", "LogbookText", "LogbookWorkbench"],
        cache="localhost",
    ),
)
