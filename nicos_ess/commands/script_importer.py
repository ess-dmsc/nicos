from nicos.commands import usercommand
from nicos import session
import inspect
import os


__all__ = [
    "import_instrument_scripts",
]

FILENAME = "commands.py"


def _import_instrument_scripts(instrument):
    # NOTE: currently we can only import one file.

    # Find the frame we want to add the commands to.
    # This will be the same frame we find the NICOS commands in.
    globs = dict()
    for i in inspect.stack():
        if "maw" in i[0].f_globals:
            globs = i[0].f_globals

    # Hackery to import the instrument commands into the same namespace as
    # the NICOS commands.
    file_loc = os.path.join(session.experiment.instrument_scripts_filepath, instrument, FILENAME)
    exec(compile(open(file_loc).read(), file_loc, "exec"), globs)
    print(f"File loc {file_loc}")


@usercommand
def import_instrument_scripts():
    _import_instrument_scripts(session.instrument.name.lower())
