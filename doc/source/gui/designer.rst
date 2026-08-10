.. _gui-designer:

Using the Qt designer with NICOS widgets
========================================

For easy programming of graphical interfaces, NICOS provides a couple of
Qt widgets that can display and edit information about NICOS devices or
device parameters.

NICOS provides the ``designer-nicos`` command that starts the Qt designer
with appropriate options to add the NICOS widgets to the Designer widget box
(see below for custom widgets).

If custom widgets should be included, give the module name or names with widget
classes on the command line. To edit an existing UI file with the standard
NICOS widgets available, run for example::

   uv run designer-nicos nicos_ess/gui/panels/ui_files/devices.ui

This opens the UI file used by
``nicos_ess.gui.panels.devices.DevicesPanel``.
