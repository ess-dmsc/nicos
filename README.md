# NICOS

## Server
Install the requirements:
```
pip install -r requirements.txt
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

## Client
Install the requirements:
```
pip install -r requirements-gui.txt
```
Start the client:
```
./bin/nicos-gui -c nico_ess/guiconfig.py
```
