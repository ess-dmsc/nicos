"""ESS Experiment device."""

import time
from os import path

from yuos_query.exceptions import BaseYuosException
from yuos_query.yuos_client import YuosCacheClient

from nicos import session
from nicos.core import (
    SIMULATION,
    Attach,
    Device,
    DevStatistics,
    Measurable,
    Param,
    Readable,
    UsageError,
    listof,
    mailaddress,
    none_or,
    oneof,
)
from nicos.core.params import expanded_path, subdir
from nicos.devices.sample import Sample
from nicos.utils import createThread, readFileCounter
from nicos_ess.devices.datamanager import DataManager


class EssExperiment(Device):
    parameters = {
        "proposal": Param(
            "Current proposal number or proposal string",
            type=str,
            default="123456",
            category="experiment",
        ),
        "propinfo": Param(
            "Dict of info for the current proposal",
            type=dict,
            default={},
            internal=True,
        ),
        "title": Param(
            "Proposal title",
            type=str,
            volatile=True,
            category="experiment",
            settable=True,
        ),
        "run_title": Param(
            "Title of the current run",
            type=str,
            settable=True,
            default="",
            category="experiment",
        ),
        "users": Param(
            "User names and emails for the proposal",
            default=[],
            type=listof(dict),
            volatile=True,
            category="experiment",
        ),
        "localcontact": Param(
            "Local contacts for current experiment",
            default=[],
            type=listof(dict),
            volatile=True,
            category="experiment",
        ),
        "cache_filepath": Param(
            "Path to the proposal cache",
            type=str,
            category="experiment",
            mandatory=True,
            userparam=False,
        ),
        "update_interval": Param(
            "Time interval (in hrs.) for proposal cache updates",
            default=1.0,
            type=float,
            userparam=False,
        ),
        "fixed_proposal_path": Param(
            "Override the generated proposal file path",
            default="/tmp/",
            type=none_or(str),
            userparam=False,
        ),
        "counterfile": Param(
            "Name of the file with data counters in dataroot and datapath",
            default="counters",
            userparam=False,
            type=subdir,
        ),
        "lastpoint": Param(
            "Last used value of the point counter - ONLY for display purposes",
            type=int,
            internal=True,
        ),
        "lastscan": Param(
            "Last used value of the scan counter - ONLY for display purposes",
            type=int,
            internal=True,
        ),
        "forcescandata": Param(
            "If true, force scan datasets to be created also for single counts",
            type=bool,
            default=False,
        ),
        "dataroot": Param(
            "Root data path under which all proposal specific paths are created",
            mandatory=True,
            type=expanded_path,
        ),
        "scripts": Param(
            "Currently executed scripts",
            type=listof(str),
            settable=True,
            internal=True,
            no_sim_restore=True,
            category="experiment",
        ),
        "errorbehavior": Param(
            "Behavior on unhandled errors in commands",
            type=oneof("abort", "report"),
            default="abort",
            settable=True,
            userparam=False,
        ),
        "detlist": Param(
            "List of default detector device names",
            type=listof(str),
            settable=True,
            internal=True,
        ),
        "envlist": Param(
            "List of default environment device names to read at every scan point",
            type=listof(str),
            settable=True,
            internal=True,
        ),
    }

    attached_devices = {
        "sample": Attach("The device object representing the sample", Sample),
    }

    datamanager_class = DataManager

    def doPreinit(self, mode):
        self.__dict__["data"] = self.datamanager_class()

    def doInit(self, mode):
        self._yuos_client = None
        self._update_proposal_cache_worker = createThread(
            "update_cache", self._update_proposal_cache, start=False
        )
        try:
            self._yuos_client = YuosCacheClient.create(self.cache_filepath)
            self._update_proposal_cache_worker.start()
        except Exception as error:
            self.log.warning("proposal look-up not available: %s", error)

    def doReadTitle(self):
        return self.propinfo.get("title", "")

    def doReadUsers(self):
        return self.propinfo.get("users", [])

    def doReadLocalcontact(self):
        return self.propinfo.get("localcontacts", [])

    def get_current_run_number(self):
        full_path = path.join(self.dataroot, self.counterfile)
        if not path.isfile(full_path):
            session.log.warning(f"No run number file found at: {full_path}")
            return None
        counterpath = path.normpath(full_path)
        nextnum = readFileCounter(counterpath, "file")
        return nextnum

    def new(self, proposal, title=None, localcontact=None, user=None, **kwds):
        if self._mode == SIMULATION:
            raise UsageError("Simulating switching experiments is not supported!")

        proposal = str(proposal)

        if not proposal.isnumeric():
            raise UsageError("Proposal ID must be numeric")

        # Handle back compatibility
        users = user if user else kwds.get("users", [])
        localcontacts = localcontact if localcontact else kwds.get("localcontacts", [])

        self._check_users(users)
        self._check_local_contacts(localcontacts)

        # combine all arguments into the keywords dict
        kwds["proposal"] = proposal
        kwds["title"] = str(title) if title else ""
        kwds["localcontacts"] = localcontacts
        kwds["users"] = users

        # give an opportunity to check proposal database etc.
        propinfo = self._newPropertiesHook(proposal, kwds)
        self._setROParam("propinfo", propinfo)
        self._setROParam("proposal", proposal)

        # Update cached values of the volatile parameters
        self._pollParam("title")
        self._pollParam("localcontact")
        self._pollParam("users")
        self._newSetupHook()
        session.experimentCallback(self.proposal, None)

    def _newPropertiesHook(self, proposal, kwds):
        """Hook for querying a database for proposal related data.

        Should return an updated kwds dictionary.
        """
        return kwds

    def _newSetupHook(self):
        """Hook for doing additional setup work on new experiments,
        after everything has been set up.
        """

    def update(self, title=None, users=None, localcontacts=None):
        self._check_users(users)
        self._check_local_contacts(localcontacts)
        title = str(title) if title else ""
        propinfo = dict(self.propinfo)
        if title is not None:
            propinfo["title"] = title
        if users is not None:
            propinfo["users"] = users
        if localcontacts is not None:
            propinfo["localcontacts"] = localcontacts
        self._setROParam("propinfo", propinfo)
        # Update cached values of the volatile parameters
        self._pollParam("title")
        self._pollParam("users")
        self._pollParam("localcontact")

    def proposalpath_of(self, proposal):
        if self.fixed_proposal_path is not None:
            return self.fixed_proposal_path
        return path.join(
            session.instrument.name.lower(), time.strftime("%Y"), proposal, "raw"
        )

    def _check_users(self, users):
        if not users:
            return
        if not isinstance(users, list):
            raise UsageError("users must be supplied as a list")

        for user in users:
            if not user.get("name"):
                raise KeyError("user name must be supplied")
            mailaddress(user.get("email", ""))

    def _check_local_contacts(self, contacts):
        if not contacts:
            return
        if not isinstance(contacts, list):
            raise UsageError("local contacts must be supplied as a list")
        for contact in contacts:
            if not contact.get("name"):
                raise KeyError("local contact name must be supplied")
            mailaddress(contact.get("email", ""))

    def finish(self):
        self.new(0, "Service mode")
        self.sample.set_samples({})

    def _canQueryProposals(self):
        if self._yuos_client:
            return True
        return False

    def _update_proposal_cache(self):
        while True:
            self._yuos_client.update_cache()
            time.sleep(self.update_interval * 3600)

    def _queryProposals(self, proposal=None, kwds=None):
        if not kwds:
            return []
        if kwds.get("admin", False):
            results = self._get_all_proposals()
        else:
            results = self._query_by_fed_id(kwds.get("fed_id", ""))

        return [
            {
                "proposal": str(prop.id),
                "title": prop.title,
                "users": self._extract_users(prop),
                "localcontacts": [],
                "samples": self._extract_samples(prop),
                "dataemails": [],
                "notif_emails": [],
                "errors": [],
                "warnings": [],
            }
            for prop in results
        ]

    def _query_by_fed_id(self, name):
        try:
            return self._yuos_client.proposals_for_user(name)
        except BaseYuosException as error:
            self.log.error("%s", error)
            raise

    def _get_all_proposals(self):
        try:
            return self._yuos_client.all_proposals()
        except BaseYuosException as error:
            self.log.error("%s", error)
            raise

    def _extract_samples(self, query_result):
        samples = []
        for sample in query_result.samples:
            samples.append(
                {
                    "name": sample.name,
                    "temperature": "0",
                    "electric_field": "0",
                    "magnetic_field": "0",
                }
            )
        return samples

    def _extract_users(self, query_result):
        users = []
        for first, last, fed_id, org in query_result.users:
            users.append(self._create_user(f"{first} {last}", "", org, fed_id))
        if query_result.proposer:
            first, last, fed_id, org = query_result.proposer
            users.append(self._create_user(f"{first} {last}", "", org, fed_id))
        return users

    def _create_user(self, name, email, affiliation, fed_id):
        return {
            "name": name,
            "email": email,
            "affiliation": affiliation,
            "facility_user_id": fed_id,
        }

    @property
    def sample(self):
        return self._attached_sample

    def get_samples(self):
        return [dict(x) for x in self.sample.samples.values()]

    def newSample(self, parameters):
        # Do not try to create unwanted directories as
        # in nicos/devices/experiment
        pass

    def setDetectors(self, detectors):
        dlist = []
        for det in detectors:
            if isinstance(det, Device):
                det = det.name
            if det not in dlist:
                dlist.append(det)
        self.detlist = dlist
        # try to create them right now
        self.detectors  # pylint: disable=pointless-statement

    @property
    def detectors(self):
        if self._detlist is not None:
            return self._detlist[:]
        detlist = []
        all_created = True
        for detname in self.detlist:
            try:
                det = session.getDevice(detname, source=self)
            except Exception:
                self.log.warning("could not create %r detector device", detname, exc=1)
                all_created = False
            else:
                if not isinstance(det, Measurable):
                    self.log.warning(
                        "cannot use device %r as a detector: it is not a Measurable",
                        det,
                    )
                    all_created = False
                else:
                    detlist.append(det)
        if all_created:
            self._detlist = detlist
        return detlist[:]

    def doUpdateDetlist(self, detectors):
        self._detlist = None  # clear list of actual devices

    def _scrubDetEnvLists(self):
        """Remove devices from detlist that don't exist anymore
        after a setup change.
        """
        newlist = []
        for devname in self.detlist:
            if devname not in session.configured_devices:
                self.log.warning(
                    "removing device %r from detector list, it "
                    "does not exist in any loaded setup",
                    devname,
                )
            else:
                newlist.append(devname)
        self.detlist = newlist

    @property
    def sampleenv(self):
        if self._envlist is not None:
            return self._envlist[:]
        devlist = []
        all_created = True
        for devname in self.envlist:
            try:
                if ":" in devname:
                    devname, stat = devname.split(":")
                    dev = session.getDevice(devname, source=self)
                    dev = DevStatistics.subclasses[stat](dev)
                else:
                    dev = session.getDevice(devname, source=self)
            except Exception:
                self.log.warning(
                    "could not create %r environment device", devname, exc=1
                )
                all_created = False
            else:
                if not isinstance(dev, (Readable, DevStatistics)):
                    self.log.warning(
                        "cannot use device %r as environment: it is not a Readable",
                        dev,
                    )
                    all_created = False
                else:
                    devlist.append(dev)
        if all_created:
            self._envlist = devlist
        return devlist[:]

    def setEnvironment(self, devices):
        dlist = []
        for dev in devices:
            if isinstance(dev, Device):
                dev = dev.name
            elif isinstance(dev, DevStatistics):
                dev = str(dev)
            if dev not in dlist:
                dlist.append(dev)
        self.envlist = dlist
        # try to create them right now
        self.sampleenv  # pylint: disable=pointless-statement
        session.elogEvent("environment", dlist)

    def doUpdateEnvlist(self, devices):
        self._envlist = None  # clear list of actual devices
