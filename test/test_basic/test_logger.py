from nicos.utils.loggers import (
    NicosLogfileHandler,
    NicosLogger,
    initLoggers,
)
from tempfile import TemporaryDirectory
import logging
import os

import time
import pytest

FAKE_TIME = 1781183150.0847485  # 2026-06-11

@pytest.fixture
def patch_time_time(monkeypatch):

    def mytime():
        return FAKE_TIME

    monkeypatch.setattr(time, 'time', mytime)


def test_log_file_handler_rollover(patch_time_time):
    global FAKE_TIME
    timeTuple = time.localtime(int(FAKE_TIME))
    year = timeTuple.tm_year
    month = timeTuple.tm_mon
    day = timeTuple.tm_mday
    max_num_files = 5
    # TODO check that 'current' symlink exists
    with TemporaryDirectory(prefix="nicos_log_pytest_") as tmpdirname:
        initLoggers()
        log = NicosLogger("pytest")
        log.parent = None
        log.setLevel(logging.DEBUG)
        log.addHandler(
            NicosLogfileHandler(os.path.join(tmpdirname, "log"), "pytest", use_subdir=False, backupCount=max_num_files)
        )
        for _d in range(10):
            log.info(f"test message on day {day}")
            print(os.listdir(os.path.join(tmpdirname,"log")))
            assert os.path.exists(os.path.join(tmpdirname, "log", f"pytest.{year}-{month:02}-{day:02}.log")), f"Log file missing for 'day' {day}"
            assert os.path.islink(os.path.join(tmpdirname, "log", "current")), f"Sym link to log file missing for 'day' {day}"
            # force rollover
            FAKE_TIME = FAKE_TIME + 24*60*60  # add one day
            timeTuple = time.localtime(int(FAKE_TIME))
            year = timeTuple.tm_year
            month = timeTuple.tm_mon
            day = timeTuple.tm_mday

        # ensure that old files have been removed: total number of files
        # should be max_num_files (i.e. backups), the current log file and
        # the symlink "current"
        assert len(os.listdir(os.path.join(tmpdirname,"log"))) == max_num_files + 2
