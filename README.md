# NICOS

## Install Server
Install the requirements (virtual environment recommended):
```
pip install -r requirements.txt
```
Create a nicos-data directory:
```
mkdir /opt/nicos-data
```
Note: may require sudo rights and additional configuring of directory ownership.

Select an instrument:
```
ln -s nicos_ess/<instrument>/nicos.conf .
```
Start the cache:
```
./bin/nicos-cache
```
In a different terminal, start the poller:
```
./bin/nicos-poller
```
In a different terminal, start the daemon:
```
./bin/nicos-daemon
```

## Install Client
Install the GUI requirements:
```
pip install -r requirements-gui.txt
```
Start the client:
```
./bin/nicos-gui -c nicos_ess/<instrument>/guiconfig.py
```
To run with QT6 (generally preferred but necessary for Mac silicon):
```
NICOS_QT=6 ./bin/nicos-gui -c nicos_ess/<instrument>/guiconfig.py
```
## Developer
Install the development requirements:
```
pip install -r requirements-dev.txt
```
Install the pre-commit hook:
```
pre-commit install
```
