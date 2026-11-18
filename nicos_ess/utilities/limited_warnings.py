import time


class LimitedWarnings:
    """Log each kind of problem as a warning at most once in *interval* seconds.

    The repeats go to the debug log, so a stream of bad messages or Kafka
    errors does not flood the log.
    """

    def __init__(self, log, interval=600):
        self._log = log
        self._interval = interval
        self._warned = {}

    def warn(self, kind, msg, *args):
        now = time.monotonic()
        if now < self._warned.get(kind, -self._interval) + self._interval:
            self._log.debug(msg, *args)
        else:
            self._warned[kind] = now
            self._log.warning(msg, *args)

    def clear(self):
        """Let each kind warn again."""
        self._warned.clear()
