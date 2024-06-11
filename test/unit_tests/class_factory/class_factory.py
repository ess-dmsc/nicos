import logging

from nicos.core import SIMULATION, ConfigurationError
from nicos.utils import HardwareStub


def base_init(self, name, **config):
    self._name = name
    self._config = {name.lower(): value for (name, value) in config.items()}
    self._params = {"name": name}
    self._infoparams = []
    self._adevs = {}
    self._sdevs = set()
    self._controllers = set()
    self._cache = None
    self.log = logging.getLogger(name)
    self.log.setLevel(logging.DEBUG)
    self.init()


def base_setattr(self, name, value):
    object.__setattr__(self, name, value)


def _initParam(self, param, paraminfo=None):
    paraminfo = paraminfo or self.parameters[param]
    done = False

    if not done and param in self._params:
        # happens when called from a param getter, not from init()
        value = self._params[param]
    elif not done:
        value = self._config.get(param, paraminfo.default)
    value = self._validateType(value, param, paraminfo)

    self._params[param] = value
    return value


def init(self):
    self._cache = None
    self._subscriptions = []
    self._mode = SIMULATION
    # self._attachDevices()

    def _init_param(param, paraminfo):
        param = param.lower()
        if paraminfo.mandatory and param not in self._config:
            raise ConfigurationError(
                self, "missing configuration " "parameter %r" % param
            )
        value = Ellipsis

        if value is not Ellipsis:
            if param in self._ownparams:
                self._params[param] = value
                return
            if param in self._config:
                value = self._validateType(self._config[param], param)

            self._params[param] = value
        else:
            self._initParam(param, paraminfo)

    later = []

    for param, paraminfo in self.parameters.items():
        if paraminfo.preinit:
            _init_param(param, paraminfo)
        else:
            later.append((param, paraminfo))

    if hasattr(self, "doPreinit"):
        self.doPreinit(self._mode)

    for param, paraminfo in later:
        _init_param(param, paraminfo)

    if hasattr(self, "doInit"):
        self.doInit(self._mode)

    self._epics_wrapper = HardwareStub(self)


def test_factory(original_class, method_overrides):
    class_name = "Testable" + original_class.__name__
    class_dict = dict(original_class.__dict__)
    for method_name, new_method in method_overrides.items():
        class_dict[method_name] = new_method
    new_class = type(class_name, original_class.__bases__, class_dict)
    return new_class


if __name__ == "__main__":
    from nicos_ess.devices.epics.area_detector import AreaDetector

    method_overrides = {
        "__init__": base_init,
        "__setattr__": base_setattr,
        "init": init,
        "_initParam": _initParam,
    }

    TestAreaDetector = test_factory(AreaDetector, method_overrides)

    test_ad = TestAreaDetector(
        name="orca_camera",
        description="The light tomography Orca camera.",
        pv_root="Orca:cam1:",
        ad_kafka_plugin="orca_kafka_plugin",
        image_topic="nido_camera",
        unit="images",
        brokers=["localhost:9092"],
        pollinterval=None,
        pva=True,
        monitor=True,
    )
