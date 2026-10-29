# Upstream NICOS

This repository tracks upstream NICOS (https://github.com/mlz-ictrl/nicos,
branch `master`) through regular git merges. Upstream code is kept as close to
upstream as possible so that merges stay small.

## Ownership

| Paths | Owner | Rule |
|---|---|---|
| `nicos/`, `nicos_demo/`, `nicos_mlz/`, `nicostools/`, `tools/`, `bin/`, `resources/`, `test/` (except the ESS paths below), `conftest.py` | upstream | taken from upstream on every sync; keep the upstream style, never ruff-format |
| `nicos_ess/`, `test/nicos_ess/`, `integration_test/`, `doc/`, `ci/`, packaging (`pyproject.toml`, `uv.lock`), CI and lint config | ESS | upstream changes to these paths are ignored |
| other upstream facilities (`nicos_sinq/`, …), upstream packaging and CI | – | not carried |

Lint (ruff, codespell, pre-commit) excludes the upstream-owned paths.

## ESS patches in upstream-owned paths

Keep this list in sync with `git diff upstream/master -- <upstream paths>`.
Everything here either goes upstream or moves into `nicos_ess/`.

| File | Change | Plan |
|---|---|---|
| `nicos/devices/epics/pva/`, `nicos/devices/epics/mixins.py` | ESS EPICS layer (p4p/caproto wrappers, subscription race fix, limits); upstream uses `nicos/devices/epics/wrapper/` | move into `nicos_ess` |
| `nicos/services/cache/database/redis.py`, `nicos/services/cache/endpoints/`, registration in `database/__init__.py` | Redis cache backend | upstream (Gerrit) |
| `nicos/__init__.py` | version from installed package metadata, git as fallback | upstream (packaging) |
| `nicos/configmod.py` | `nicos_root` for wheel installs; `nicos.conf` from site/user config dirs | upstream (packaging) |
| `nicos/services/poller/__init__.py` | find `nicos-poller` on `PATH` | upstream (packaging) |
| `nicos/core/sessions/__init__.py` | `experiment` sysconfig accepts any `Device` (`EssExperiment`) | upstream or subclass `Experiment` |
| `nicos/core/sessions/setups.py` | `pnp_pv_root` setup key (`nicos_ess.devices.pnp_listener`) | upstream |
| `nicos/utils/__init__.py` | also hide `pw*`/`token*` locals in logged tracebacks (the keystore holds the Kafka password in `pw`) | upstream (security) |
| `nicos/services/daemon/proto/classic.py` | copy handler list before broadcasting (client disconnect race) | upstream |
| `nicos/guisupport/timeseries.py` | fix `ndarray.resize` misuse when the buffer is full | upstream |
| `nicos/guisupport/qt.py` | default to Qt6 on Apple silicon | upstream |
| `bin/nicos-gui` | start `nicos_ess.gui.main` | keep |
| `resources/nicos-gui.qrc`, `resources/material/icons/`, `nicos/guisupport/gui_rc_qt*.py` | four extra ESS icons, ESS versions of two icons; logos of facilities we do not carry removed | upstream icons; keep logo removal |
| `test/utils.py` | elog start timeout 5 s instead of 2 s (CI runners are slower) | upstream |
| `test/bin/simulate` | put the checkout root, not `test/`, on `sys.path` (else `test/nicos_ess` shadows `nicos_ess`) | upstream (bug) |
| `test/test_custom/test_dryrun.py` | skip `nicos_mlz` instrument dry runs | keep |
| `nicos_demo/pyproject.toml`, `test/test_basic/test_{cache_numpy,timeseries}.py`, `test/test_epics/`, `test/test_redis/`, `test/setups/custom/ess_*.py`, `test/setups/custom/estia_*.py` | ESS-only files | keep / move with their code |

## Syncing

```
python3 ci/sync_upstream.py
```

The script merges `upstream/master` without committing, keeps our side of all
ESS-owned paths, drops paths we do not carry, and prints conflicts, upstream
dependency changes and whether the GUI resources changed. Then:

1. Resolve conflicts in the upstream-owned paths, keeping the patches above.
2. Port dependency changes from upstream's `setup.py`/`requirements*.txt` to
   `pyproject.toml` and run `uv lock`.
3. If `resources/nicos-gui.qrc` changed, drop the logos of facilities we do not
   carry from it and regenerate the resource modules:
   `uv run python -m PyQt5.pyrcc_main -o nicos/guisupport/gui_rc_qt5.py resources/nicos-gui.qrc` and
   `uvx --from pyside6-essentials pyside6-rcc -g python resources/nicos-gui.qrc | sed s,PySide6,PyQt6, > nicos/guisupport/gui_rc_qt6.py`.
4. Run `tools/check-setups` on every `nicos_ess` setup directory and the test
   suite.
5. Commit the merge and open a merge request. Merge it without squashing: the
   merge commit's upstream parent is what makes the next sync incremental.

A pipeline schedule with `UPSTREAM_SYNC=1` runs the same trial merge, the
setup check and the tests, and fails when upstream has introduced conflicts or
breakage.
