from nicos import session
from nicos.commands import usercommand

__all__ = ["set_title"]


@usercommand
def set_title(title):
    """Set the run title of the current experiment.

    Example:

    >>> set_title('Ni powder reference scan')
    """
    session.experiment.run_title = title
