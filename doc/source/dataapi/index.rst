========
Data API
========

.. module:: nicos.core.data.sink
   :noindex:

--------
Overview
--------

.. digraph:: DataAPI

    rankdir = LR;

    subgraph cluster0 {
        node [style=filled,color=white];
        style = "rounded,filled";
        color = lightsalmon;

        "commands" {rank = same; "data-manager";}
        "detectors" {rank = same; "devices";}
        "data-sets" {rank = same; "data-sinks"}

        "devices" -> "data-manager";
        "detectors" -> "data-manager";
        "commands" -> "data-manager";
        "data-manager" -> "data-sets";
        "data-sets" -> "data-sinks";

    }

The data handling in NICOS is split into three main parts:

 - The commands, which are intended to write data files, interact with the data
   manager and this will interact with the data sinks.

 - The :ref:`data sinks <data_sinks>` may write data into file, transfer the
   data (for example to a preview), or do nothing with the data.

 - The :ref:`data manager <data_manager>` collects the data from the detector(s)
   as well as the data from the different devices (as so called metadata).  The
   collected data and metadata will be stored in :ref:`data sets <data_sets>`.
   The data manager sends exactly these data sets to data sinks where they will
   be analyzed and handled.

Each data sink handles the data sent from the data manager individually.  It is
not only how the data will be treated, but also which type of data set it
handles.  This selection will be done via the :attr:`~DataSink.settypes`
parameter of each data sink and can be activated for the different types of data
sets.

These data sets are different for a scan, a subscan, or a single count command.

---------------------------------------------------
Interaction of commands with data manager and sinks
---------------------------------------------------

Count command
~~~~~~~~~~~~~

.. module:: nicos.commands.measure
   :noindex:

If the user calls the :func:`~count` command in NICOS the following happens:

Interaction of count command, data manager, and data sink:

#. The count command calls ``beginPoint`` on the data manager, which
   initializes a ``PointDataset`` and calls ``prepare`` and ``begin`` on the
   data sinks.
#. The count command calls ``updateMetainfo`` on the data manager, which
   collects the metainfo and forwards it to the data sinks via
   ``putMetainfo``.
#. The count command starts the detectors and waits until they are finished
   or stopped.  Whenever the cache sends an updated value to the data
   manager, it is forwarded to the data sinks via ``putValues``.
#. When the detectors are finished or stopped, the count command reads the
   detector data.
#. The count command calls ``putResults`` on the data manager, which forwards
   the results to the data sinks via ``putResults``.
#. The count command calls ``finishPoint`` on the data manager, which calls
   ``end`` on the data sinks.

Scan command
~~~~~~~~~~~~~

.. module:: nicos.commands.scan
   :noindex:

In case of calling the :func:`~scan` or related command there is the following
interaction between the components:

Interaction of a scan command, data manager, and data sink:

#. The scan command calls ``beginScan`` on the data manager, which
   initializes a ``ScanDataset`` and calls ``prepare`` and ``begin`` on the
   data sinks.
#. For every scan point, the scan command:

   #. calls ``beginPoint`` on the data manager, which initializes a
      ``PointDataset`` and calls ``prepare`` and ``begin`` on the data sinks,
   #. moves the devices and reads the new positions,
   #. calls ``putValues`` on the data manager with the updated positions,
      which are forwarded to the data sinks via ``putValues``,
   #. starts counting,
   #. calls ``updateMetainfo`` on the data manager, which forwards the
      metainfo of the point dataset to the data sinks via ``putMetainfo``,
   #. waits until counting is finished,
   #. calls ``finishPoint`` on the data manager, which calls ``end`` on the
      data sinks for the point dataset.
#. The scan command calls ``finishScan`` on the data manager, which calls
   ``end`` on the data sinks for the scan dataset.

----------
Components
----------

.. toctree::
   :maxdepth: 1

   datamanager
   datasets
   datasinks
