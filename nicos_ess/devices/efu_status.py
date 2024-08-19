from subprocess import CalledProcessError, check_output

from nicos.core import Override, Param, Readable, host, status
from nicos.utils import parseHostPort

DEFAULT_EFU_PORT = 8888


class EFUStatus(Readable):
    """
    This device reports Event Formation Unit status.
    """

    parameters = {
        "ipconfig": Param(
            "IP and port configuration",
            type=host(defaultport=DEFAULT_EFU_PORT),
            mandatory=True,
            userparam=False,
        ),
    }

    parameter_overrides = {
        "unit": Override(mandatory=False, settable=False, volatile=False),
    }

    # key-value pairs translating integer values to an EFU status.
    _stat_to_status = {
        0: (status.ERROR, "EFU offline"),
        1: (status.WARN, "Processing and output stages inactive"),
        2: (status.WARN, "Input and output stages inactive"),
        3: (status.WARN, "Output stage inactive"),
        4: (status.WARN, "Input and processing stage inactive"),
        5: (status.WARN, "Processing stage inactive"),
        6: (status.WARN, "Input stage inactive"),
        7: (status.OK, ""),
    }

    def doInit(self, mode):
        efu_host, efu_port = parseHostPort(self.ipconfig, DEFAULT_EFU_PORT)
        self._command = f'echo "RUNTIMESTATS" | nc {efu_host} {efu_port}'

    def doRead(self, maxage=0):
        return ""

    def doStatus(self, maxage=0):
        unknown_status = (status.ERROR, "Status could not be retrieved")
        try:
            # The command will return an integer value which translates into a
            # status of the EFU.
            raw_stat = check_output(self._command, shell=True)
            stat = int(raw_stat.split()[-1])
            return self._stat_to_status.get(stat, unknown_status)
        except (ValueError, IndexError, CalledProcessError) as e:
            self.log.error("Could not correctly access EFU status. " "Error was: %s", e)
            return unknown_status
