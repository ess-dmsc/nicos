from nicos import session
from nicos.commands import usercommand


@usercommand
def set_title(title):
    session.experiment.run_title = title
