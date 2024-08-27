"""ESS Experiment device."""

import time
from os import path

from yuos_query.exceptions import BaseYuosException
from yuos_query.yuos_client import YuosCacheClient

from nicos import session
from nicos.core import (
    SIMULATION,
    Override,
    Param,
    UsageError,
    listof,
    mailaddress,
    none_or,
)
from nicos.devices.experiment import Experiment
from nicos.utils import createThread, readFileCounter

from nicos_ess.devices.datamanager import DataManager


class EssExperiment(Experiment):
    parameters = {
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
            default=None,
            type=none_or(str),
            userparam=False,
        ),
        "run_title": Param(
            "Title of the current run",
            type=str,
            settable=True,
            default="",
            category="experiment",
        ),
    }

    parameter_overrides = {
        "propprefix": Override(default=""),
        "proptype": Override(settable=True),
        "serviceexp": Override(default="Service"),
        "sendmail": Override(default=False, settable=False),
        "zipdata": Override(default=False, settable=False),
        "users": Override(default=[], type=listof(dict)),
        "localcontact": Override(default=[], type=listof(dict)),
        "title": Override(settable=True),
        "elog": Override(default=False, settable=False),
    }

    datamanager_class = DataManager

    def doInit(self, mode):
        Experiment.doInit(self, mode)
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
        if not path.isfile(path.join(self.dataroot, self.counterfile)):
            session.log.warning(
                f"No run number file at: {path.join(self.dataroot, self.counterfile)}"
            )
            return None
        counterpath = path.normpath(path.join(self.dataroot, self.counterfile))
        nextnum = readFileCounter(counterpath, "file")
        return nextnum

    def new(self, proposal, title=None, localcontact=None, user=None, **kwds):
        if self._mode == SIMULATION:
            raise UsageError("Simulating switching experiments is not " "supported!")

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
        self.proptype = "service" if proposal == "0" else "user"

        # Update cached values of the volatile parameters
        self._pollParam("title")
        self._pollParam("localcontact")
        self._pollParam("users")
        self._newSetupHook()
        session.experimentCallback(self.proposal, None)

    def update(self, title=None, users=None, localcontacts=None):
        self._check_users(users)
        self._check_local_contacts(localcontacts)
        title = str(title) if title else ""
        Experiment.update(self, title, users, localcontacts)

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

    def get_samples(self):
        return [dict(x) for x in self.sample.samples.values()]

    def newSample(self, parameters):
        # Do not try to create unwanted directories as
        # in nicos/devices/experiment
        pass
