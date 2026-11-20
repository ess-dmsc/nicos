from test.nicos_ess.gui.doubles import EXP_PANEL_PROPOSAL_EVAL
from test.nicos_ess.gui.helpers import (
    get_panel_by_class,
    single_panel_guiconfig_string,
)

guiconfig_string = single_panel_guiconfig_string(
    "nicos_ess.gui.panels.exp_panel.ExpPanel"
)


PROPOSAL = {
    "proposal": "123098",
    "title": "A mock proposal for mucking about",
    "users": [
        {
            "name": "Doe",
            "email": "doe@facility.org",
            "affiliation": "The Facility",
            "facility_user_id": "111222333",
        }
    ],
    "localcontacts": [],
    "samples": [{"material": "mocka"}],
    "dataemails": [],
    "notif_emails": [],
    "errors": [],
    "warnings": [],
}

PROPOSAL_EVAL = {
    "session.experiment._queryProposals(kwds={'fed_id': 'test', 'admin': True})": [
        PROPOSAL
    ],
    EXP_PANEL_PROPOSAL_EVAL: (
        PROPOSAL["proposal"],
        PROPOSAL["title"],
        PROPOSAL["users"],
        PROPOSAL["localcontacts"],
        "report",
    ),
    f"Exp.new(title='{PROPOSAL['title']}', "
    f"localcontacts={PROPOSAL['localcontacts']}, "
    f"users={PROPOSAL['users']}, proposal='{PROPOSAL['proposal']}')": None,
}


def test_exppanel_starts(gui_window_factory):
    window = gui_window_factory(guiconfig_string=guiconfig_string)
    panel = get_panel_by_class(window, "nicos_ess.gui.panels.exp_panel.ExpPanel")

    assert panel.isVisible() is True


def test_exppanel_can_apply_changes(fake_daemon, gui_window_factory, qtbot):
    fake_daemon.evals.update(
        {
            "Exp.update(title='', localcontacts=[], users=[])": None,
            "session.experiment._canQueryProposals()": True,
        }
    )

    window = gui_window_factory(guiconfig_string=guiconfig_string)
    panel = get_panel_by_class(window, "nicos_ess.gui.panels.exp_panel.ExpPanel")

    assert panel.proposalNum.text() == ""

    # check button states
    assert panel.applyWarningLabel.isVisible() is False
    assert panel.btn_apply.isVisible() is False
    assert panel.queryDBButton.isVisible() is True

    # seed the proposal information
    fake_daemon.evals.update(PROPOSAL_EVAL)

    # query the DB
    panel.queryDBButton.click()
    assert panel.applyWarningLabel.isVisible() is True
    assert panel.btn_apply.isVisible() is True
    assert panel.proposalNum.text() == "123098"

    # apply
    panel.btn_apply.click()
    assert panel.proposalNum.text() == "123098"
    assert panel.applyWarningLabel.isVisible() is False
    assert panel.btn_apply.isVisible() is False
