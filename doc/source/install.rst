.. _install-nicos:

Installing NICOS
================

Get the source code
-------------------

The NICOS source is hosted in the `ESS GitLab project
<https://gitlab.esss.lu.se/ecdc/ess-dmsc/nicos>`_. Clone it over HTTPS::

  git clone https://gitlab.esss.lu.se/ecdc/ess-dmsc/nicos.git

Or use SSH::

  git clone git@gitlab.esss.lu.se:ecdc/ess-dmsc/nicos.git

Issues and merge requests are handled in the same GitLab project.


Install the development environment
-----------------------------------

NICOS uses `uv <https://docs.astral.sh/uv/>`_ to manage Python and its
dependencies.  The required native build packages are
``pkgconf-pkg-config`` and ``systemd-devel`` on RHEL-based systems, or
``build-essential``, ``python3-dev``, ``libsystemd-dev`` and ``pkg-config``
on Debian-based systems.  A GUI installation additionally needs the native
Qt 5 and Qt WebEngine development packages.

From a source checkout, create the development environment with::

  uv sync --all-packages --extra gui

NICOS commands can then be run in that environment, for example::

  uv run nicos-demo


Configure for experimenting
---------------------------

Now you can start the individual :ref:`components <components>`.  A setup that
uses all the major components can be started with the single command::

  uv run nicos-demo

This starts the cache, poller, electronic logbook, and daemon services, and also
starts the graphical interface and a status monitor.

It will load the demo setups from ``nicos_demo/demo/setups``.  The startup setup
contains a few devices that show basic usage of the NICOS system.  Call
``help()`` to get a list of commands.  You can also call ``help(dev)`` to get
help for an individual device.

.. You can continue with :ref:`the first steps <firststeps>` from here.


Configure and build the distribution
------------------------------------

Build the core package with ``uv build``. Use ``uv build --package <name>`` for
one workspace package or ``uv build --all-packages`` for all packages. The
source distributions and wheels are written to ``dist``.
