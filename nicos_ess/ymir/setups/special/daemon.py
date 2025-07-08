description = "setup for the execution daemon"
group = "special"

devices = dict(
    LocalAuth=device(
        "nicos.services.daemon.auth.list.Authenticator",
        hashing="md5",
        passwd=[
            ("guest", "", "guest"),
            ("user", "ee11cbb19052e40b07aac0ca060c23ee", "user"),
            ("admin", "21232f297a57a5a743894a0e4a801fc3", "admin"),
        ],
    ),
    LDAPAuth=device(
        "nicos_ess.devices.auth.ldap.Authenticator",
        uri=["dc01.esss.lu.se", "dc02.esss.lu.se", "dc03.esss.lu.se"],
        userbasedn="dc=esss,dc=lu,dc=se",
        grouproles={"ECDC": "user", "ECDC SE": "user"},
    ),
    Daemon=device(
        "nicos.services.daemon.NicosDaemon",
        server="",
        servercls="nicos.services.daemon.proto.fastapi.Server",
        authenticators=["LocalAuth", "LDAPAuth"],
        loglevel="debug",
    ),
)

startupcode = """
"""
