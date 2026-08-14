from nicos.commands import usercommand
from nicos import session
import inspect
import importlib
import sys


__all__ = [
    "import_instrument_scripts",
]


def _import_instrument_scripts(instrument):
    # Add instrument scripts directory to import path.
    sys.path.insert(1, session.experiment.instrument_scripts_filepath)

    # Find the frame we want to add the commands to.
    # This will be the same frame we find the NICOS commands in.
    globs = dict()
    for i in inspect.stack():
        if "maw" in i[0].f_globals:
            globs = i[0].f_globals

    # Import the module so we can get the correct path
    inst_mod = importlib.import_module(instrument)
    file_loc = inst_mod.__file__[:-1] if inst_mod.__file__.endswith(".pyc") else inst_mod.__file__
    print(f"File loc {file_loc}")

    # Hackery to import the instrument commands into the same namespace as
    # the NICOS commands.
    exec(compile(open(file_loc).read(), file_loc, "exec"), globs)


@usercommand
def import_instrument_scripts():
    _import_instrument_scripts(session.instrument.name.lower())
