"""NICOS GUI application startup."""

import argparse
import logging
import os
import sys
import traceback
from os import path

from nicos import config
from nicos.clients.base import ConnectionData
from nicos.clients.gui.config import processGuiConfig
from nicos.clients.gui.dialogs.instr_select import InstrSelectDialog
from nicos.clients.gui.utils import DebugHandler
from nicos.guisupport.qt import QApplication
from nicos.protocols.daemon.classic import DEFAULT_PORT
from nicos.utils import importString, parseConnectionString
from nicos.utils.loggers import (
    ColoredConsoleHandler,
    NicosLogfileHandler,
    NicosLogger,
    initLoggers,
)

# Work around a crash on Py3/Bionic when readline is imported later in
# a callback from unpickling server data.
try:
    import readline  # pylint: disable=unused-import
except ImportError:
    pass

log = None


def parseargs():
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "-c",
        "--config-file",
        dest="configfile",
        default=None,
        help="use the configuration file CONFIGFILE",
    )
    parser.add_argument(
        "-v",
        "--view-only",
        dest="viewonly",
        default=False,
        action="store_true",
        help="run in view-only mode",
    )
    parser.add_argument(
        "connect",
        nargs="?",
        default=None,
        help="""A connection string with the following form:

                        [user_name[:password[@host[:port]]]]""",
    )
    parser.add_argument(
        "-s",
        "--server",
        dest="server",
        default="localhost",
        help="the default NICOS server to connect to",
    )
    parser.add_argument(
        "-u",
        "--user",
        dest="user",
        default=None,
        help="the suggested user to log on as",
    )
    return parser.parse_args()


def main(argv):
    global log  # pylint: disable=global-statement

    userpath = path.join(path.expanduser("~"), ".config", "nicos")

    # Set up logging for the GUI instance.
    initLoggers()
    log = NicosLogger("gui")
    log.parent = None
    log.setLevel(logging.INFO)
    log.addHandler(ColoredConsoleHandler())
    log.addHandler(
        NicosLogfileHandler(path.join(userpath, "log"), "gui", use_subdir=False)
    )

    # set up logging for unhandled exceptions in Qt callbacks
    def log_unhandled(*exc_info):
        traceback.print_exception(*exc_info)
        log.exception("unhandled exception in QT callback", exc_info=exc_info)

    sys.excepthook = log_unhandled

    app = QApplication(argv, organizationName="nicos", applicationName="gui")

    opts = parseargs()

    if opts.configfile is None:
        try:
            config.apply()
        except RuntimeError:
            pass
        # If "demo" is detected automatically, let the user choose their
        # instrument configuration.
        need_dialog = config.instrument is None or (
            config.setup_package == "nicos_demo"
            and config.instrument == "demo"
            and "INSTRUMENT" not in os.environ
        )
        if need_dialog:
            opts.configfile = InstrSelectDialog.select(
                "Your instrument could not be automatically detected."
            )
            if opts.configfile is None:
                return
        else:
            opts.configfile = path.join(
                config.setup_package_path, *config.instrument.split("."), "guiconfig.py"
            )

    with open(opts.configfile, "rb") as fp:
        configcode = fp.read()
    gui_conf = processGuiConfig(configcode)
    gui_conf.stylefile = ""

    if gui_conf.options.get("facility") in ["ess", "sinq"]:
        gui_conf.stylefile = f"{config.nicos_root}" f"/nicos_ess/gui/guiconfig.qss"

    stylefiles = [
        path.join(userpath, "style-%s.qss" % sys.platform),
        path.join(userpath, "style.qss"),
        path.splitext(opts.configfile)[0] + "-%s.qss" % sys.platform,
        path.splitext(opts.configfile)[0] + ".qss",
    ]

    for stylefile in [gui_conf.stylefile] or stylefiles:
        if path.isfile(stylefile):
            try:
                with open(stylefile, "r", encoding="utf-8") as fd:
                    app.setStyleSheet(fd.read())
                gui_conf.stylefile = stylefile
                break
            except Exception:
                log.warning("Error setting user style sheet from %s", stylefile, exc=1)

    mainwindow_cls = importString(
        gui_conf.options.get(
            "mainwindow_class", "nicos.clients.gui.mainwindow.MainWindow"
        )
    )
    mainwindow = mainwindow_cls(log, gui_conf, opts.viewonly, opts.server, opts.user)
    log.addHandler(DebugHandler(mainwindow))

    if opts.connect:
        parsed = parseConnectionString(opts.connect, DEFAULT_PORT)
        if parsed:
            cdata = ConnectionData(**parsed)
            cdata.viewonly = opts.viewonly
            mainwindow.setConnData(cdata)
            if cdata.password is not None:
                # we have a password, connect right away
                mainwindow.client.connect(mainwindow.conndata)
            else:
                # we need to ask for password, override last preset (uses given
                # connection data) and force showing connect window
                mainwindow.lastpreset = ""
                mainwindow.autoconnect = True
    mainwindow.startup()

    return app.exec()
