# NICOS

## Install Server
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

## Install Client
Install the GUI requirements:
```
pip install -r requirements-gui.txt
```
Start the client:
```
./bin/nicos-gui -c nico_ess/guiconfig.py
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
