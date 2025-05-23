description = "Email and SMS notifiers"

group = "lowlevel"

devices = dict(
    email=device(
        "nicos.devices.notifiers.Mailer",
        description="Reports via email",
        mailserver="mailhost.frm2.tum.de",
        sender="panda@frm2.tum.de",
        copies=[("astrid.schneidewind@frm2.tum.de", "important")],
        subject="[PANDA]",
    ),
    email1=device(
        "nicos.devices.notifiers.Mailer",
        mailserver="mailhost.frm2.tum.de",
        sender="panda@frm2.tum.de",
        receivers=[
            "h.kleines@fz-juelich.de",
            "i.radelytskyi@fz-juelich.de",
            "astrid.schneidewind@frm2.tum.de",
            "s.neumair@fz-juelich.de",
        ],
        subject="[PANDA warning]",
    ),
    email2=device(
        "nicos.devices.notifiers.Mailer",
        mailserver="mailhost.frm2.tum.de",
        sender="panda@frm2.tum.de",
        receivers=["astrid.schneidewind@frm2.tum.de"],
        subject="[PANDA]",
    ),
    email3=device(
        "nicos.devices.notifiers.Mailer",
        mailserver="mailhost.frm2.tum.de",
        sender="panda@frm2.tum.de",
        receivers=["astrid.schneidewind@frm2.tum.de"],
        subject="[PANDA]",
    ),
    smser=device(
        "nicos.devices.notifiers.SMSer",
        server="triton.admin.frm2",
        receivers=["015788345341"],
    ),
    smsastr=device(
        "nicos.devices.notifiers.SMSer",
        server="triton.admin.frm2",
        receivers=["01795385391"],
    ),
)
