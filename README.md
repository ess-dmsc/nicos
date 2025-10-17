# NICOS

## Installing the Server Locally

To set up the NICOS server on your local machine, follow these steps.

### Step 1: Install the Required Python Packages

Install the necessary Python packages (it's recommended to use a virtual environment):
```bash
pip install -r requirements.txt
```

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
./bin/nicos-cache
```

To configure what cache database to use, see section [Configure Cache Database](#configure-cache-database).

### Step 5: Start the Poller

In a separate terminal, start the NICOS poller:
```bash
./bin/nicos-poller
```

### Step 6: Start the Collector (Optional)

If required, start the NICOS collector in another terminal:
```bash
./bin/nicos-collector
```

### Step 7: Start the Daemon

Finally, in another terminal, start the NICOS daemon:
```bash
./bin/nicos-daemon
```

## Install Client

### Step 1: Install GUI Requirements

Install the necessary packages for the NICOS GUI:
```bash
pip install -r requirements-gui.txt
```

### Step 2: Start the Client

Start the NICOS client with your selected instrument's configuration:
```bash
./bin/nicos-gui -c nicos_ess/<instrument>/guiconfig.py
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
