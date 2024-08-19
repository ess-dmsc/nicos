"""ESS datamanager device."""

import os

from nicos import session
from nicos.core.data.manager import DataManager as BaseDataManager
from nicos.utils import readFileCounter, updateFileCounter


class DataManager(BaseDataManager):
    def incrementCounters(self, countertype):
        """Increment the counters for the given *countertype*.

        This should update the counter files accordingly.

        Returns a list of (counterattribute, value) tuples to set on the
        dataset.
        """
        exp = session.experiment
        filepath = os.path.join(exp.dataroot, exp.counterfile)
        if not os.path.isfile(filepath):
            session.log.warning("creating new empty file counter file at %s", filepath)
        nextnum = readFileCounter(filepath, countertype) + 1
        updateFileCounter(filepath, countertype, nextnum)
        return [("counter", nextnum)]
