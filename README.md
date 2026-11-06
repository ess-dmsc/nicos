# NICOS (ESS fork)

This is a forked version of NICOS for use at the European Spallation Source (ESS). For the original upstream version, please visit https://nicos-controls.org/

## Installation

Prerequisites:

- Install `uv` ([see the uv installation instructions](https://docs.astral.sh/uv/getting-started/installation/))
- Install necessary system packages:
  - on RHEL-based systems: `dnf install pkgconf-pkg-config systemd-devel`
  - on Debian-based systems: `apt install build-essential python3-dev libsystemd-dev pkg-config`
- For the GUI, you will need some native libraries installed:
  - on RHEL-based systems: `dnf install python3-qt5`
  - on Debian-based systems: `apt install qtbase5-dev qtwebengine5-dev`

Some useful uv commands:

    uv python list: show available Python versions (both system-wide and those managed by uv).
    uv tree: print a dependency tree of the current project.
    uv run: execute a command from the current project.
    uv venv: create a virtual environment.


### Local development environment

Inside the repository, first use `uv sync` to create a local virtual environment with the specific packages and extras you want:

    uv sync --all-packages --extra gui

This will build all packages (use --package <name> for specific packages or leave out for only the core) and install all dependencies including the `gui` optional ones.

After this, run:

    % uv run | grep nicos
    - designer-nicos
    - nicos-aio
    - nicos-cache
    - nicos-client
    - nicos-collector
    - nicos-daemon
    - nicos-demo
    ...

    % uv run nicos-gui

to start any of the scripts directly. Note that you will have to prefix these commands when mentioned in the sections below with `uv run`.

You can also install NICOS into the uv managed tools to have its commands available inside your `PATH`:

    uv tool install nicos

### Building the NICOS core and plug-in packages

- run `uv build` from the package root directory to build (only) the core package.
- run `uv build --package <name>` to build a specific package, e.g. `nicos_demo`.
- run `uv build --all-packages` to build all available packages.

The resulting source tarball and wheel files will be located in the `dist` directory.

## Installing the Server Locally {#localserver}

To set up the NICOS server on your local machine, follow these steps.

### Step 1: Install NICOS

Follow one of the described methods above to install NICOS locally.

Note that `confluent-kafka` requires `librdkafka`, which may result in this step failing if the wheel needs to be built in your environment

### Step 2: Create a Data Directory

Create a directory for storing NICOS data:
```bash
mkdir /opt/nicos-data
```
> *Note: This may require sudo rights. Ensure the directory has the correct ownership.*

### Step 3: Select an Instrument Configuration

Link the configuration file for your chosen instrument or copy it at the location described in the [section "Configure NICOS"](#nicosconf). If you are using the default location on a Linux-based system, this would be:
```bash
ln -s nicos_ess/<instrument>/nicos.conf ~/.config/nicos/nicos.conf
```

A good starting instrument is `ymir`, which is our physical test instrument in B02.

### Step 4: Start the Cache

Start the NICOS cache server:
```bash
nicos-cache
```

To configure what cache database to use, see section [Configure Cache Database](#configurecache).

### Step 5: Start the Poller

In a separate terminal, start the NICOS poller:
```bash
nicos-poller
```

### Step 6: Start the Collector (Optional)

If required, start the NICOS collector in another terminal:
```bash
nicos-collector
```

### Step 7: Start the Daemon

Finally, in another terminal, start the NICOS daemon:
```bash
nicos-daemon
```

## Install Client

### Step 1: Install GUI Requirements

Install the necessary packages for the NICOS GUI by following the installation instructions above.

### Step 2: Start the Client

Start the NICOS client with your selected instrument's configuration:
```bash
nicos-gui -c nicos_ess/<instrument>/guiconfig.py
```

### Step 3: Run with QT6 (Needed for Mac Silicon)

If you prefer QT6 or use macOS with silicon architecture, use the following commands:
```bash
uv sync --all-packages --extra gui_qt6
NICOS_QT=6 ./bin/nicos-gui -c nicos_ess/<instrument>/guiconfig.py
```

The first one has to be only run once (and is not necessary on macOS as it is picked as default).


## Configure NICOS {#nicosconf}

Place the NICOS configuration file (`nicos.conf`) for your choice of instrument into one of the following locations, searched in order:

- in the site-wide directory, i.e. `/etc/xdg/nicos/nicos.conf` on GNU/Linux, or
- the `nicos` directory in your standard user configuration path, i.e. on GNU/Linux systems, this would be `~/.config/nicos/nicos.conf`.

Both these paths can be modified by setting the `XDG_CONFIG_DIRS` or `XDG_CONFIG_HOME` environment variable, respectively, to point to a different location.
See [the corresponding XDG variable documentation](https://platformdirs.readthedocs.io/en/latest/parameters.html#xdg-env-vars) for reference.

For backwards compatibility, the `nicos_root` folder (i.e. the root of the repository) will be searched first.
When NICOS has been deployed as package, this path would most likely not point to a suitable location.
Therefore, prefer the XDG standard directories as place for `nicos.conf`

### Configure Cache Database {#configurecache}

NICOS supports different cache databases. You can use `MemoryCacheDatabase`, `FlatfileCacheDatabase`, or `RedisCacheDatabase`. For local development, `MemoryCacheDatabase` or `FlatfileCacheDatabase` are easiest to set up.

#### Step 1: Selecting the Cache Database

Edit the `cache.py` setup file to choose your cache database:
```bash
vim nicos_ess/<instrument>/setups/special/cache.py
```

#### Step 2: Configuration Options

##### Option 1: MemoryCacheDatabase (Default)
No changes needed if you are using the default `MemoryCacheDatabase`:
```python
DB=device(
    "nicos.services.cache.database.MemoryCacheDatabase",
    loglevel="info",
)
```

##### Option 2: FlatfileCacheDatabase
To use `FlatfileCacheDatabase`, update the setup file as follows:
```python
DB=device(
    "nicos.services.cache.database.FlatfileCacheDatabase",
    storepath="/opt/nicos-data/cache",
    loglevel="info",
)
```

##### Option 3: RedisCacheDatabase
For Redis-based caching, `RedisCacheDatabase`, configure as follows:
```python
DB=device(
    "nicos.services.cache.database.RedisCacheDatabase",
    historydays=14,
    # Flat numeric tuples, lists and dictionaries up to this size use native
    # RedisTimeSeries component series.
    maxnativecomponents=50,
    # Serialized text and mixed or larger structures are not archived by
    # default. Set a short retention period here to opt in.
    arbitraryhistorydays=None,
    loglevel="info",
)
```

`historydays` controls native RedisTimeSeries retention for scalar numbers and
flat, fully numeric tuples, lists and dictionaries. `maxnativecomponents` limits
how many component series one value may create. Device status is treated
separately: its numeric status code is archived natively while its descriptive
text remains part of the current value. If a native structure changes shape or
container type at runtime, its existing component history is replaced so that
older samples cannot be reconstructed with the wrong layout.

The separate `arbitraryhistorydays` setting controls serialized history for
text, mixed structures and numeric structures above the native component limit;
`None` disables it, `0` keeps it indefinitely, and a positive value retains
that many days. Current values are stored regardless of the history setting.
When arbitrary history is disabled, its old history keys are removed the next
time that value is reported. Each report with a new timestamp is archived even
if its value is unchanged.

In the case of `RedisCacheDatabase`, you need to set up Redis and RedisTimeSeries.


## Developer Setup

### Install Pre-Commit Hook

Install the pre-commit hook to ensure code quality:
```bash
pre-commit install
```

---
