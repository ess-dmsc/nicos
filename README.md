# NICOS

## Configure NICOS

Place the NICOS configuration file (`nicos.conf`) of your choice into the `nicos` directory in your standard user configuration path.
This particular path differs between platforms: on GNU/Linux systems, this would be `~/.config/nicos/nicos.conf`.

## Installation

Prerequisites: Install `uv` ([see the uv installation instructions](https://docs.astral.sh/uv/getting-started/installation/)
)

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


## Installing the Server Locally

To set up the NICOS server on your local machine, follow these steps.

### Step 1: Install NICOS

Follow one of the described methods above to install NICOS locally.

### Step 2: Create a Data Directory

Create a directory for storing NICOS data:
```bash
mkdir /opt/nicos-data
```
> *Note: This may require sudo rights. Ensure the directory has the correct ownership.*

### Step 3: Select an Instrument Configuration

Link the configuration file for your chosen instrument:
```bash
ln -s nicos_ess/<instrument>/nicos.conf .
```

A good starting instrument is `ymir`, which is a test instrument.

### Step 4: Start the Cache

Start the NICOS cache server:
```bash
nicos-cache
```

To configure what cache database to use, see section [Configure Cache Database](#configure-cache-database).

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

### Step 3: Run with QT6 (For Mac Silicon)

If you prefer QT6, use the following command (not required on macOS with silicon architecture):
```bash
NICOS_QT=6 ./bin/nicos-gui -c nicos_ess/<instrument>/guiconfig.py
```
## Configure Cache Database

NICOS supports different cache databases. You can use `MemoryCacheDatabase`, `FlatfileCacheDatabase`, or `RedisCacheDatabase`. For local development, `MemoryCacheDatabase` or `FlatfileCacheDatabase` are easiest to set up.

### Step 1: Selecting the Cache Database

Edit the `cache.py` setup file to choose your cache database:
```bash
vim nicos_ess/<instrument>/setups/special/cache.py
```

### Step 2: Configuration Options

#### Option 1: MemoryCacheDatabase (Default)
No changes needed if you are using the default `MemoryCacheDatabase`:
```python
DB=device(
    "nicos.services.cache.server.MemoryCacheDatabase",
    loglevel="info",
)
```

#### Option 2: FlatfileCacheDatabase
To use `FlatfileCacheDatabase`, update the setup file as follows:
```python
DB=device(
    "nicos.services.cache.server.FlatfileCacheDatabase",
    storepath="/opt/nicos-data/cache",
    loglevel="info",
)
```

#### Option 3: RedisCacheDatabase
For Redis-based caching, `RedisCacheDatabase`, configure as follows:
```python
DB=device(
    "nicos.services.cache.server.RedisCacheDatabase",
    loglevel="info",
)
```

In the case of `RedisCacheDatabase`, you need to set up Redis and RedisTimeSeries. See section [Redis Setup](#redis-setup) for instructions.

## Developer Setup

### Step 1: Install Development Requirements

To set up your environment for development, install the additional required packages:
```bash
pip install -r requirements-dev.txt
```

### Step 2: Install Pre-Commit Hook

Install the pre-commit hook to ensure code quality:
```bash
pre-commit install
```

# Redis Setup

This section guides you through installing Redis, an in-memory data store, and RedisTimeSeries, a module for time-series data processing.
The RedisTimeSeries module is mandatory.

The instructions are for Linux systems (tested on ubuntu 22.04 and CentOS 7). For other operating systems, refer to the Redis and RedisTimeSeries documentation.

## Installing Redis

### Step 1: Download and Extract Redis

Download and extract the Redis package:
```bash
wget http://download.redis.io/releases/redis-6.2.14.tar.gz
tar xzf redis-6.2.14.tar.gz
cd redis-6.2.14
```

### Step 2: Compile Redis

Compile the Redis source code:
```bash
make
```
> *Optional but recommended: Run tests to ensure Redis is functioning correctly.*
```bash
make test
```
Install Redis on your system:
```bash
sudo make install
```

### Step 3: Configuration File Setup

Create a directory for the Redis configuration file:
```bash
sudo mkdir /etc/redis
```
Copy the default configuration file:
```bash
sudo cp redis.conf /etc/redis/redis.conf
```

### Step 4: Edit the Redis Configuration

Open the configuration file to apply necessary settings:
```bash
sudo vim /etc/redis/redis.conf
```
> **IMPORTANT:** Ensure Redis is bound to localhost for security:
```bash
bind 127.0.0.1 ::1
protected-mode yes
supervised systemd
dir /var/lib/redis
```

### Step 5: Create a Systemd Service File for Redis

Create a service file to manage Redis with systemd:
```bash
sudo vim /etc/systemd/system/redis.service
```
Paste the following configuration, replacing `nicos` with your username (on the nicosservers, it's `nicos`):
```ini
[Unit]
Description=Redis In-Memory Data Store
After=network.target

[Service]
User=nicos
Group=nicos
ExecStart=/usr/local/bin/redis-server /etc/redis/redis.conf
ExecStop=/usr/local/bin/redis-cli shutdown
Restart=always

[Install]
WantedBy=multi-user.target
```

### Step 6: Prepare the Redis Data Directory

Create and set permissions for the Redis data directory:
```bash
sudo mkdir /var/lib/redis
sudo chown nicos:nicos /var/lib/redis
sudo chmod 770 /var/lib/redis
```

### Step 7: Enable and Start the Redis Service

Enable and start the Redis service:
```bash
sudo systemctl enable redis
sudo systemctl start redis
```
> *Optionally, check the status to ensure Redis is running smoothly:*
```bash
sudo systemctl status redis
```

### Step 8: Configure the System PATH

Find the Redis CLI tool:
```bash
sudo find / -name redis-cli
```
Add Redis binaries to your system PATH:
```bash
vim ~/.bashrc
export PATH=$PATH:/usr/local/bin
source ~/.bashrc
```

### Step 9: Verify Redis Installation

Test that Redis is installed and running correctly:
```bash
redis-cli ping
```

## Installing RedisTimeSeries

### Step 1: Clone and Set Up RedisTimeSeries

Clone the RedisTimeSeries repository:
```bash
git clone --recursive https://github.com/RedisTimeSeries/RedisTimeSeries.git -b v1.8.10
cd RedisTimeSeries
```
Set up the environment and build the module:
```bash
./sbin/setup
bash -l
make
```

### Step 2: Install RedisTimeSeries Module

Copy the RedisTimeSeries module to the appropriate directory:
```bash
cp RedisTimeSeries/bin/linux-x64-release/redistimeseries.so /etc/redis/redistimeseries.so
```

### Step 3: Load RedisTimeSeries Module in Redis

To load the RedisTimeSeries module, add this line to `redis.conf`:
```bash
loadmodule /etc/redis/redistimeseries.so
```
Restart Redis to apply changes:
```bash
sudo systemctl restart redis
```

### Step 4: Verify Module Installation

Check that the RedisTimeSeries module is loaded correctly:
```bash
redis-cli MODULE LIST
```
---
