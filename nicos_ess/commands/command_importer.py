from nicos.commands import usercommand
from nicos import session
import inspect
import os


__all__ = [
    "import_instrument_commands",
]

FILENAME = "commands.py"


def _import_instrument_commands(file_location):
    # NOTE: this only allows us to import one file, so instruments
    # will have to put all their commands in one file.

    # Find the frame we want to add the commands to.
    # This will be the same frame we find the NICOS commands in.
    globs = dict()
    for i in inspect.stack():
        if "maw" in i[0].f_globals:
            globs = i[0].f_globals

    # Hackery to import the instrument commands into the same namespace as
    # the NICOS commands.
    exec(compile(open(file_location).read(), file_location, "exec"), globs)


@usercommand
def import_instrument_commands():
    file = os.path.join(session.experiment.instrument_scripts_directory, session.instrument.name.lower(), FILENAME)
    if not os.path.isfile(file):
        raise RuntimeError(f"Instrument command file does not exist. Expected path is {file}")

    _import_instrument_commands(file)
