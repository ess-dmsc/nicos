Getting Started
===============

Launching the NICOS GUI
------------------------

To start NICOS:

1. Open the **Start menu** or press the **Start** key on your keyboard.
2. Type **NICOS** and open the **NICOS GUI** application.

If the **login window appears**, enter your **username** and **password**.

If the login window does **not** appear:

- Click the **cogwheel icon** in the top-right corner.
- Select **Connect to server...**
- Enter your **LDAP credentials** to log in.

Using the Interface
-------------------

Once logged in, you can navigate the following tabs:

- **Experiment** – Choose proposals and edit samples.
- **Setup** – Select and load devices.
- **Instrument interaction** – Run commands and view output.
- **Scan Plot**, **Detector Image**, **Beamline Panel** – View live plots (only visible while in the *Instrument interaction* tab).
- **Scripting** – Write and execute custom Python scripts.
- **History** – Explore historical data and device values.

Basic Command Examples
----------------------

Counting with Detectors
^^^^^^^^^^^^^^^^^^^^^^^

To perform a basic count, you must first specify the detector(s) you want to use using :py:func:`nicos.commands.measure.SetDetectors`.
Each detector can have multiple channels.

For example, the detector ``jbi_detector`` may include:

- ``timer`` – time-based counting
- ``pulse_counter`` – pulse-based counting
- ``multiblade_detector`` – event-based counting

Example usage:

.. code-block:: python

   # Set the active detector
   SetDetectors(jbi_detector)

   # Count for 30 seconds
   count(timer=30)

   # Count until 200 events on the multiblade detector
   count(mb_det=200)

   # Count until EVR counter reaches 100
   count(pulse_counter=100)

   # Start a live acquisition
   live()

   # Stop the acquisition
   jbi_detector.stop()

For full documentation, see:

- :py:func:`nicos.commands.measure.count`
- :py:func:`nicos.commands.measure.live`
- :py:func:`nicos.commands.measure.SetDetectors`

Scanning Motors
^^^^^^^^^^^^^^^

To perform a scan across motor positions, use the :py:func:`nicos.commands.scan.scan` function.

Before scanning, you need to set your detector(s) using :py:func:`nicos.commands.measure.SetDetectors` as described above.

Example:

.. code-block:: python

   # Set the active detector
   SetDetectors(jbi_detector)

   # Perform a scan
   scan(motor_x, [0, 10, 20, 30], timer=30)

This moves the motor ``motor_x`` to 0, 10, 20, and 30 degrees, and performs a 30-second count at each position.

Writing NeXus Files
^^^^^^^^^^^^^^^^^^^

To write data to a NeXus file, use the :py:func:`nicos_ess.commands.filewriter.nexusfile_open` function.
This is best done in a script using a context manager:

.. code-block:: python

   TIME = 30
   SCAN_POINTS = [0, 10, 20, 30]

   # Start writing a NeXus file using a context manager
   with nexusfile_open("This is the title of my NeXus file"):
       scan(motor_x, SCAN_POINTS, timer=TIME)
   # The file is automatically closed when exiting the 'with' block

Using a context manager is the **recommended approach** as it ensures the file is always properly closed,
even if an error occurs during execution.

Alternatively, you can manually start and stop file writing:

.. code-block:: python

   TIME = 30
   SCAN_POINTS = [0, 10, 20, 30]

   # Start writing a NeXus file
   start_filewriting("This is the title of my NeXus file")

   # Perform a scan
   scan(motor_x, SCAN_POINTS, timer=TIME)

   # Stop writing the file
   stop_filewriting()

For more information, see:

- :py:func:`nicos_ess.commands.filewriter.nexusfile_open`
- :py:func:`nicos_ess.commands.filewriter.start_filewriting`
- :py:func:`nicos_ess.commands.filewriter.stop_filewriting`

Troubleshooting
---------------

- **Commands not executing?**

  Make sure you're connected to the server (see *Launching the NICOS GUI*). Look in the upper right corner and make sure it does not say **DISCONNECTED** .

- **Devices or detectors missing?**

  Ensure the correct instrument setup is loaded in the **Setup** tab.

- **Script errors or file writing failures?**

  Test your commands manually before putting them in a script.
  When writing NeXus files, prefer the context manager approach to avoid leaving files open.

- **Still stuck?**

  Use :py:func:`nicos.commands.basic.help()` or :py:func:`nicos.commands.basic.ListCommands()` to explore available commands in NICOS.

------------------
