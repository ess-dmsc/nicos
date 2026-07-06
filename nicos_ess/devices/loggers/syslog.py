"""Module for custom facility logger and formatter that logs via the syslog facilities."""

from logging.handlers import SysLogHandler
from logging import (
    DEBUG,
    ERROR,
    INFO,
    WARNING,
    Formatter,
    Handler,
    Logger,
    LogRecord,
    addLevelName,
    CRITICAL,
)
import sys
import time
import traceback
from typing import override

from nicos.utils.loggers import ACTION, StreamHandler


class NicosSyslogFormatter(Formatter):
    """
    A formatter for syslog that can be understood by rsyslog for filtering by log level.
    """

    def __init__(self, fmt=None, datefmt=None):
        super().__init__(fmt, datefmt)

    def formatTime(self, record, datefmt=None):
        return time.strftime(
            datefmt or "%b %d %H:%M:%S", self.converter(record.created)
        )

    def format(self, record):
        # Define the log level string
        loglevel = record.levelname

        # Define the syslog priority
        priority = self._get_syslog_priority(record.levelno)
        message = record.getMessage()

        # Construct the syslog message
        syslog_message = f"<{priority}>{record.name}: {loglevel} {message}"

        return syslog_message

    def _get_syslog_priority(self, levelno):
        # Mapping of log level numbers to syslog priorities
        if levelno >= CRITICAL:
            return SysLogHandler.LOG_CRIT
        elif levelno >= ERROR:
            return SysLogHandler.LOG_ERR
        elif levelno >= WARNING:
            return SysLogHandler.LOG_WARNING
        elif levelno >= INFO:
            return SysLogHandler.LOG_INFO
        elif levelno >= DEBUG:
            return SysLogHandler.LOG_DEBUG
        else:
            return SysLogHandler.LOG_NOTICE


class NicosSysLogHandler(StreamHandler):
    """
    A handler class that writes records to standard output in journal format.
    """

    def __init__(self):
        StreamHandler.__init__(self, sys.stdout)
        self.setFormatter(NicosSyslogFormatter())

    @override
    def emit(self, record, fs="%s\n"):
        """Emit log record filtering out records with ACTION level."""
        if record.levelno == ACTION:
            # do not write ACTIONs to syslog, they're only for the UI
            return
        super().emit(record, fs)


def create_syslog_log_handlers(config):
    """Create, configure and return a Syslog log handler if running in daemon mode."""
    from nicos import session

    if session._daemon_mode:
        return [NicosSysLogHandler()]
    return []
