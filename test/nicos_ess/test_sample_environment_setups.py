import logging
from pathlib import Path

import pytest

from nicos.configmod import readToml
from nicos.core.sessions.setups import make_configdata, readSetups
from nicos.utils.files import iterSetups

NICOS_ESS = Path(__file__).parents[2] / "nicos_ess"
SHARED_DIR = (NICOS_ESS / "sample_environment" / "setups").resolve()
LOG = logging.getLogger(__name__)
INSTRUMENT_DIRS = {
    conf.parent.relative_to(NICOS_ESS).as_posix(): [
        str((conf.parent.parent / subdir / "setups").resolve())
        for subdir in readToml(str(conf))["nicos"]["setup_subdirs"]
    ]
    for conf in [*NICOS_ESS.glob("*/nicos.conf"), *NICOS_ESS.glob("labs/*/nicos.conf")]
}
INSTRUMENTS = sorted(INSTRUMENT_DIRS)

session_setup = None


@pytest.fixture(scope="module")
def shared_setups():
    return readSetups([str(SHARED_DIR)], LOG)


@pytest.fixture(scope="module")
def instrument_setups():
    return {name: readSetups(dirs, LOG) for name, dirs in INSTRUMENT_DIRS.items()}


def _configdata(instrument, name):
    all_setups = dict(iterSetups(INSTRUMENT_DIRS[instrument]))
    return make_configdata("", all_setups, set())(name)


def test_equipment_is_plug_and_play_with_a_presence_signal(shared_setups):
    for name, info in shared_setups.items():
        if info["group"] in ("lowlevel", "configdata"):
            continue
        assert info["group"] == "plugplay", name
        assert info["extended"]["presence_signal"].startswith("pva://"), name


@pytest.mark.parametrize("instrument", INSTRUMENTS)
def test_forwarded_pvs_use_the_instrument_topic(instrument, instrument_setups):
    topic = _configdata(instrument, "config.SAMPLE_ENV_TOPIC")
    assert topic == f"{instrument.split('/')[-1]}_sample_env"
    setups = instrument_setups[instrument]
    for name, info in setups.items():
        if info is None or not str(info["_filenames_"][0]).startswith(str(SHARED_DIR)):
            continue
        for devname, (_, config) in info["devices"].items():
            for entry in config.get("nexus_config", []):
                if "source_name" in entry:
                    assert entry["topic"] == topic, f"{name}: {devname}"


@pytest.mark.parametrize("instrument", INSTRUMENTS)
def test_instrument_uses_the_shared_setups(instrument):
    assert str(SHARED_DIR) in INSTRUMENT_DIRS[instrument]


@pytest.mark.parametrize("instrument", INSTRUMENTS)
def test_instrument_does_not_shadow_a_shared_setup(instrument, shared_setups):
    own = set()
    for setup_dir in INSTRUMENT_DIRS[instrument]:
        if setup_dir != str(SHARED_DIR):
            own |= {name for name, _ in iterSetups([setup_dir])}
    assert own & set(shared_setups) == {"config"}


@pytest.mark.parametrize("instrument", INSTRUMENTS)
def test_instrument_watches_equipment_presence(instrument, instrument_setups):
    system = instrument_setups[instrument]["system"]
    assert "sample_environment_presence" in system["includes"]


@pytest.mark.parametrize("instrument", INSTRUMENTS)
def test_poller_always_watches_equipment_presence(instrument, instrument_setups):
    # the daemon only tells the poller its setups once one is loaded as master,
    # so the presence would not be watched after a fresh start without this
    _, config = instrument_setups[instrument]["poller"]["devices"]["Poller"]
    assert "sample_environment_presence" in config["alwayspoll"]
