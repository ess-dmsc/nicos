"""NICOS GUI experiment setup window."""

from copy import deepcopy

from nicos.clients.gui.panels.setup_panel import ProposalDelegate, combineUsers
from nicos.clients.gui.utils import dialogFromUi, loadUi
from nicos.core import ADMIN
from nicos.guisupport.qt import (
    QAbstractItemView,
    QHeaderView,
    QIntValidator,
    QListWidgetItem,
    Qt,
    pyqtSlot,
)
from nicos.guisupport.tablemodel import TableModel
from nicos.utils import decodeAny, findResource
from nicos_ess.gui.panels.panel import PanelBase

USER_FIELDS = ["name", "email", "affiliation"]
CONTACT_FIELDS = ["name", "email", "affiliation"]


class ProposalSettings:
    def __init__(
        self,
        proposal_id="",
        title="",
        users=None,
        local_contacts=None,
        abort_on_error=True,
        notifications=None,
        samples=None,
    ):
        self.proposal_id = proposal_id
        self.title = title
        self.users = users if users else []
        self.local_contacts = local_contacts if local_contacts else [{}]
        self.samples = samples if samples else []
        self.notifications = notifications if notifications else []
        self.abort_on_error = abort_on_error

    def __eq__(self, other):
        return (
            self.proposal_id == other.proposal_id
            and self.title == other.title
            and self.users == other.users
            and self.local_contacts == other.local_contacts
            and self.notifications == other.notifications
            and self.abort_on_error == other.abort_on_error
            and self.samples == other.samples
        )


class ExpPanel(PanelBase):
    """Provides a panel with several input fields for the experiment settings."""

    panelName = "Experiment setup"

    def __init__(self, parent, client, options):
        PanelBase.__init__(self, parent, client, options)
        loadUi(self, findResource("nicos_ess/gui/panels/ui_files/exp_panel.ui"))

        self.old_settings = ProposalSettings()
        self.new_settings = ProposalSettings()

        self._user_fields = USER_FIELDS
        self.to_monitor = ["sample/samples", "exp/propinfo"]
        self.users_model = TableModel(self._user_fields)
        self.users_model.data_updated.connect(self._check_for_changes)
        self.userTable.setModel(self.users_model)
        self.userTable.horizontalHeader().setSectionResizeMode(
            QHeaderView.ResizeMode.Stretch
        )

        self.contacts_model = TableModel(CONTACT_FIELDS)
        self.contacts_model.insert_row(0)
        self.contacts_model.data_updated.connect(self._check_for_changes)
        self.contactsTable.setModel(self.contacts_model)
        self.contactsTable.horizontalHeader().setSectionResizeMode(
            QHeaderView.ResizeMode.Stretch
        )

        self.proposalNum.setValidator(QIntValidator(0, 999999999))

        self._text_controls = (self.propTitle, self.proposalNum)
        self._tables = (self.contactsTable, self.userTable)

        # When set, samples from a queried proposal are not sent to the daemon.
        self.hide_samples = options.get("hide_sample", False)
        self._setup_warning_label()
        self.initialise_connection_status_listeners()

    def _setup_warning_label(self):
        self.applyWarningLabel.setStyleSheet("color: red")
        self.applyWarningLabel.setVisible(False)

    @pyqtSlot()
    def on_btn_apply_clicked(self):
        self.applyChanges()

    @pyqtSlot()
    def on_btn_discard_clicked(self):
        self.discardChanges()

    def _set_buttons_and_warning_behaviour(self, value):
        self.btn_apply.setVisible(value)
        self.btn_discard.setVisible(value)
        self.applyWarningLabel.setVisible(value)

    def initialise_connection_status_listeners(self):
        PanelBase.initialise_connection_status_listeners(self)
        self.client.experiment.connect(self.on_experiment_finished)
        self.client.setup.connect(self.on_client_setup)
        for monitor in self.to_monitor:
            self.client.register(self, monitor)

    def on_keyChange(self, key, value, time, expired):
        if key in self.to_monitor:
            self._update_proposal_info()

    def _update_proposal_info(self):
        values = self.client.eval(
            "session.experiment.proposal, "
            "session.experiment.title, "
            "session.experiment.users, "
            "session.experiment.localcontact, "
            "session.experiment.errorbehavior",
            None,
        )
        notif_emails = self.client.eval(
            'session.experiment.propinfo["notif_emails"]', []
        )

        samples = self.client.eval("session.experiment.get_samples()", {})

        if values:
            users = [dict(user) for user in values[2]]
            contacts = [dict(contact) for contact in values[3]]
            self.old_settings = ProposalSettings(
                decodeAny(values[0]),
                decodeAny(values[1]),
                users,
                contacts,
                values[4] == "abort",
                notif_emails,
                samples,
            )
            self.new_settings = deepcopy(self.old_settings)
            self._update_panel()

    def _update_panel(self):
        self.proposalNum.setText(self.old_settings.proposal_id)
        self.propTitle.setText(self.old_settings.title)
        self.errorAbortBox.setChecked(self.old_settings.abort_on_error)
        self._update_users_model(self.old_settings.users)
        self._update_contacts_model(self.old_settings.local_contacts)

    def on_client_connected(self):
        PanelBase.on_client_connected(self)
        self._update_proposal_info()
        self._is_proposal_system_available()

    def _is_proposal_system_available(self):
        available = self.client.eval("session.experiment._canQueryProposals()", False)
        self.queryDBButton.setVisible(available)
        self.proposalNum.setReadOnly(available)
        self.propTitle.setReadOnly(available)
        self.addUserButton.setVisible(not available)
        self.deleteUserButton.setVisible(not available)
        self.set_table_read_only(self.userTable, available)

    def set_table_read_only(self, table, read_only):
        if read_only:
            table.setEditTriggers(QAbstractItemView.EditTrigger.NoEditTriggers)
        else:
            table.setEditTriggers(
                QAbstractItemView.EditTrigger.AnyKeyPressed
                | QAbstractItemView.EditTrigger.EditKeyPressed
                | QAbstractItemView.EditTrigger.DoubleClicked
            )

    def on_client_disconnected(self):
        for control in self._text_controls:
            control.setText("")
        self._update_users_model([])
        self._update_contacts_model([])
        self.old_settings = ProposalSettings()
        self.new_settings = ProposalSettings()
        PanelBase.on_client_disconnected(self)

    def on_client_setup(self, data):
        if "system" in data[0]:
            self._is_proposal_system_available()
            self._update_proposal_info()

    def setViewOnly(self, viewonly):
        for control in self._text_controls:
            control.setEnabled(not viewonly)
        for table in self._tables:
            self.set_table_read_only(table, viewonly)
        self.errorAbortBox.setEnabled(not viewonly)
        self.queryDBButton.setEnabled(not viewonly)
        self.addUserButton.setEnabled(not viewonly)
        self.queryDBButton.setEnabled(not viewonly)
        self.deleteUserButton.setEnabled(not viewonly)
        if viewonly:
            self._set_buttons_and_warning_behaviour(False)
        else:
            self._check_for_changes()
            self._is_proposal_system_available()

    def applyChanges(self):
        self.queryDBButton.setFocus()
        if self.mainwindow.current_status != "idle":
            self.showInfo("Cannot change settings while a script is running!")
            return
        try:
            self._set_experiment()
            self._set_samples()
            self._set_notification_receivers()
            self._set_abort_on_error()
            self._update_proposal_info()
        except Exception as error:
            self.showError(str(error))

    def _set_experiment(self):
        local_contacts = [
            contact
            for contact in self.contacts_model.raw_data
            if contact.get("name", None)
        ]

        users = [
            user
            for user in self.users_model.raw_data
            if any(user.get(field) for field in self._user_fields)
        ]

        exp_args = {
            "title": self.new_settings.title,
            "localcontacts": local_contacts,
            "users": users,
        }

        if self.new_settings.proposal_id != self.old_settings.proposal_id:
            exp_args["proposal"] = self.new_settings.proposal_id
            command = "Exp.new"
        else:
            command = "Exp.update"
        args = ", ".join(f"{key}={value!r}" for key, value in exp_args.items())
        self.client.eval(f"{command}({args})")

    def _set_samples(self):
        if self.hide_samples or self.new_settings.samples == self.old_settings.samples:
            return

        samples = {}
        for index, sample in enumerate(self.new_settings.samples):
            if not sample.get("samplename", ""):
                sample["samplename"] = f"sample {index + 1}"
            samples[index] = sample
        self.client.run(f"Exp.sample.set_samples({dict(samples)})")

    def _set_abort_on_error(self):
        abort_on_error = self.new_settings.abort_on_error
        if abort_on_error != self.old_settings.abort_on_error:
            self.client.run(f"SetErrorAbort({abort_on_error})")

    def _set_notification_receivers(self):
        notifications = self.new_settings.notifications
        if notifications != self.old_settings.notifications:
            receivers = ", ".join(map(repr, notifications))
            self.client.run(f"SetMailReceivers({receivers})")

    @pyqtSlot()
    def on_addUserButton_clicked(self):
        self.users_model.insert_row(self.users_model.num_entries)

    @pyqtSlot()
    def on_deleteUserButton_clicked(self):
        to_remove = {
            index.row()
            for index in self.userTable.selectedIndexes()
            if index.isValid() and index.row() < self.users_model.num_entries
        }
        self.users_model.remove_rows(to_remove)

    @pyqtSlot()
    def on_queryDBButton_clicked(self):
        try:
            kwds = {
                "fed_id": self.parentwindow.client.login,
                "admin": self.parentwindow.client.user_level == ADMIN,
            }
            result = self.client.eval(
                f"session.experiment._queryProposals(kwds={kwds})"
            )

            if result:
                if len(result) > 1:
                    result = self.choose_proposal(result)
                    if not result:
                        return
                else:
                    result = result[0]
                    # check for errors/warnings:
                    if result.get("errors"):
                        self.showError(
                            "Proposal cannot be performed:\n\n"
                            + "\n".join(result["errors"])
                        )
                        return
                if result.get("warnings"):
                    self.showError(
                        "Proposal might have problems:\n\n"
                        + "\n".join(result["warnings"])
                    )
                # now transfer it into gui
                self.proposalNum.setText(result.get("proposal", ""))
                self.propTitle.setText(result.get("title", ""))
                self._update_users_model(result.get("users", []))
                self._update_contacts_model(result.get("localcontacts", []))
                self._update_samples(result["samples"])
            else:
                self.showError("No proposals found")
        except Exception as e:
            self.log.warning("error in proposal query", exc=1)
            self.showError(f"Querying proposal management system failed: {e}")

    def _update_users_model(self, users):
        self.users_model.raw_data = deepcopy(users)

    def _update_contacts_model(self, contacts):
        self.contacts_model.raw_data = deepcopy(contacts or [{}])

    def choose_proposal(self, proposals):
        dlg = dialogFromUi(self, "panels/setup_exp_proposal.ui")
        dlg.list.setItemDelegate(ProposalDelegate(dlg))
        for prop in proposals:
            prop_copy = deepcopy(prop)
            prop_copy["users"] = [{"name": combineUsers(prop["users"])}]
            item = QListWidgetItem("", dlg.list)
            item.setData(Qt.ItemDataRole.UserRole, prop_copy)
        if not dlg.exec():
            return
        sel = dlg.list.currentRow()
        return proposals[sel]

    def _update_samples(self, samples):
        if not self.hide_samples:
            self.new_settings.samples = deepcopy(samples)
            self._check_for_changes()

    @pyqtSlot(str)
    def on_proposalNum_textChanged(self, value):
        self.new_settings.proposal_id = value.strip()
        self._check_for_changes()

    @pyqtSlot(str)
    def on_propTitle_textChanged(self, value):
        self.new_settings.title = value.strip()
        self._check_for_changes()

    @pyqtSlot()
    def on_errorAbortBox_clicked(self):
        self.new_settings.abort_on_error = self.errorAbortBox.isChecked()
        self._check_for_changes()

    def _normalise_contacts(self, contacts):
        return [{k: contact.get(k, "") for k in CONTACT_FIELDS} for contact in contacts]

    def _check_for_changes(self):
        new_contacts = self._normalise_contacts(self.contacts_model.raw_data)
        old_contacts = self._normalise_contacts(self.old_settings.local_contacts)

        has_changed = any(
            (
                self.new_settings != self.old_settings,
                self.users_model.raw_data != self.old_settings.users,
                new_contacts != old_contacts,
            )
        )

        self._set_buttons_and_warning_behaviour(has_changed)

    def discardChanges(self):
        self._update_proposal_info()
        self._check_for_changes()

    def on_experiment_finished(self):
        self._update_proposal_info()
        self._check_for_changes()
