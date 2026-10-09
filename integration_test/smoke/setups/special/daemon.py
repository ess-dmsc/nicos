description = "setup for the execution daemon (smoke integration)"
group = "special"

devices = dict(
    Auth=device(
        "nicos.services.daemon.auth.list.Authenticator",
        hashing="md5",
        passwd=[
            ("guest", "", "guest"),
            # md5 of CANARIES["daemon login password"] in run_smoke_stack.py
            ("user", "b4bac7706b62a5f8e82b523bcc08ba43", "user"),
            ("admin", "21232f297a57a5a743894a0e4a801fc3", "admin"),
        ],
    ),
    Daemon=device(
        "nicos.services.daemon.NicosDaemon",
        server=configdata("config.DAEMON_HOST"),
        authenticators=["Auth"],
        loglevel="debug",
    ),
)

startupcode = """
"""
