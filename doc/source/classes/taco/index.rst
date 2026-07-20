.. _taco:

============
Taco classes
============

These classes serve to interface with Taco devices.  Generally the corresponding
Taco Python modules need to be installed.

For example, the temperature control classes need the ``Temperature`` module from
the ``taco-client-temperature`` package.

All classes described here are re-exported in the :mod:`nicos.devices.taco` module, so
for example both ``devices.taco.AnalogOutput`` and ``devices.taco.io.AnalogOutput``
are valid entries for the class name in a setup file.

.. toctree::
   :maxdepth: 1

   core
   detector
   axis
   power
   temperature
   io
