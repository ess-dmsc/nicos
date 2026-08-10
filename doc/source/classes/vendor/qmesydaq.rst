QMesyDAQ classes
================

These classes are for integration of detectors with MesyTec hardware and
controlled by |qmesydaq_link|.

All classes are channels and must be combined to a detector device with the
:class:`~nicos.devices.generic.detector.Detector`.

There are two versions communication with QMesyDAQ:

 - `TANGO`_
 - `TACO`_

TANGO
-----

.. automodule:: nicos.devices.vendor.qmesydaq.tango

TACO
----

.. automodule:: nicos.devices.vendor.qmesydaq.taco


.. |qmesydaq_link| raw:: html

   <a href="https://www.qmesydaq.org" target="_blank">QMesyDAQ</a>
