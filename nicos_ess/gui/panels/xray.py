"""NICOS X-ray panel."""

from nicos.clients.gui.panels import Panel
from nicos.guisupport.qt import (
    QWidget, 
    QPushButton,
    QLineEdit, 
    QHBoxLayout, 
    QVBoxLayout,
    QFormLayout, 
    pyqtSlot
)
from nicos_ess.gui.panels.live_pyqt import LiveDataPanel

class XrayPanel(Panel):
    def __init__(self, parent, client, options):
        Panel.__init__(self, parent, client, options)

        # Get devices.
        self.devmodel = options.get("model")
        self.devstatus = options.get("status")
        self.devbeam_align = options.get("beam_align")
        self.devinterlock = options.get("interlock")
        self.devxray = options.get("xray")
        self.devvoltage = options.get("voltage")
        self.devvoltage_r = options.get("voltage_r")
        self.devcurrent = options.get("current")
        self.devcurrent_r = options.get("current_r")
        self.devfocus = options.get("focus")
        self.devvacuum = options.get("vacuum")
        self.devtemperature = options.get("temperature")
        self.devalign_x = options.get("align_x")
        self.devalign_y = options.get("align_y")
        self.devcamera = options.get("camera")
        self.devcollector = options.get("collector")

        # Base layout.
        self.window = QWidget(self) #put self as argument for it to stay within the panel
        self.layout = QVBoxLayout(self.window)
        self.layouta = QHBoxLayout()
        self.layoutb = QHBoxLayout()
        self.layout.addLayout(self.layouta)
        self.layout.addLayout(self.layoutb)

        self.create_buttons_xray()
        self.panel = LiveDataPanel(parent, client, options) #can also use MultiLiveDataPanel
        self.panel.update_widget_to_show(True) #shows 2D-image
        self.create_buttons_detector()

        # Initiate.
        self.window.show()

        client.setup.connect(self.on_client_setup) #keeps running until setup is ready

    def create_buttons_xray(self):
        # Basic command buttons.
        self.bxray = QPushButton(f"X-ray", self)
        self.bwarmup = QPushButton(f"Warmup", self)
        self.breset = QPushButton(f"Reset", self)
        #self.button1.setFixedSize(120, 60)
        #self.button1.setGeometry(500, 500, 100, 50)

        # Basic command button layout.
        self.layout1 = QVBoxLayout()
        self.layouta.addLayout(self.layout1)
        self.layout1.addWidget(self.bxray)
        self.layout1.addWidget(self.bwarmup)
        self.layout1.addWidget(self.breset)

        # Read-only parameters.
        self.bmodel = QLineEdit("Model", self, readOnly=True)
        self.bstatus = QLineEdit("Status", self, readOnly=True)
        self.bbeam_align = QLineEdit("Beam Alignment Status", self, readOnly=True)
        self.binterlock = QLineEdit("Interlock Status", self, readOnly=True)
        self.bvacuum = QLineEdit("Vacuum Level Check", self, readOnly=True)
        self.btemperature = QLineEdit("Temperature Check", self, readOnly=True)

        # Read-only layout.
        self.layout2 = QFormLayout()
        self.layouta.addLayout(self.layout2)
        self.layout2.addWidget(self.bmodel)
        self.layout2.addWidget(self.bstatus)
        self.layout2.addWidget(self.bbeam_align)
        self.layout2.addWidget(self.binterlock)
        self.layout2.addWidget(self.bvacuum)
        self.layout2.addWidget(self.btemperature)

        # Read-and-write parameters.
        self.bvoltage = QPushButton("Voltage", self)
        self.bwvoltage = QLineEdit("", self)
        self.brvoltage = QLineEdit("", self, readOnly=True)
        self.bcurrent = QPushButton("Current", self)
        self.bwcurrent = QLineEdit("", self)
        self.brcurrent = QLineEdit("", self, readOnly=True)
        self.bfocus = QPushButton("Focus", self)
        self.bwfocus = QLineEdit("", self)
                
        # Read-and-write layout.
        self.layout3 = QFormLayout()
        self.layouta.addLayout(self.layout3)
        self.layout3.addRow(self.bvoltage, self.bwvoltage)
        self.layout3.addRow(self.bcurrent, self.bwcurrent)
        self.layout3.addRow(self.bfocus, self.bwfocus)

        self.layout4 = QFormLayout()
        self.layouta.addLayout(self.layout4)
        self.layout4.addWidget(self.brvoltage)
        self.layout4.addWidget(self.brcurrent)

        # Align parameters.
        self.balign_x = QPushButton("Set X-dir Object Align", self)
        self.bwalign_x = QLineEdit("")
        self.balign_y = QPushButton("Set Y-dir Object Align", self)
        self.bwalign_y = QLineEdit("")
        self.balign_beam = QPushButton("Start Beam Alignment", self)
        self.balign_all = QPushButton("Start Overall Alignment", self)
        self.balign_stop = QPushButton("Stop Beam Alignment", self)

        # Align layout.
        self.layout5 = QFormLayout()
        self.layouta.addLayout(self.layout5)
        self.layout5.addRow(self.balign_x, self.bwalign_x)
        self.layout5.addRow(self.balign_y, self.bwalign_y)
        self.layout5.addWidget(self.balign_beam)
        self.layout5.addWidget(self.balign_all)
        self.layout5.addWidget(self.balign_stop)

    def create_buttons_detector(self):
        self.bstart = QPushButton("Acquire Start", self)
        self.bstop = QPushButton("Acquire Stop", self)
        self.bacquire_time = QPushButton("Exposure Time", self)
        self.bwacquire_time = QLineEdit("", self)
        self.bacquire_period = QPushButton("Acquire Period", self)
        self.bwacquire_period = QLineEdit("", self)

        # General layout for this part.
        self.layout_detector = QHBoxLayout()
        self.layoutb.addLayout(self.layout_detector)

        # Controls for camera/detector layout.
        self.layout_controls = QFormLayout()
        self.layout_detector.addLayout(self.layout_controls)
        self.layout_controls.addRow(self.bstart, self.bstop)
        self.layout_controls.addRow(self.bacquire_time, self.bwacquire_time)
        self.layout_controls.addRow(self.bacquire_period, self. bwacquire_period)

        # Panel layout.
        self.panel.setMaximumSize(600, 600)
        self.layout_detector.addWidget(self.panel)


    # Commands to control the devices.
    def load_data(self):
        # Read parameter values.
        vmodel = self.client.getDeviceParam(self.devmodel, "value")
        vstatus = self.client.getDeviceParam(self.devstatus, "value")
        vbeam_align = self.client.getDeviceParam(self.devbeam_align, "value")
        vinterlock = self.client.getDeviceParam(self.devinterlock, "value")

        vvoltage = self.client.getDeviceParam(self.devvoltage, "value")
        vcurrent = self.client.getDeviceParam(self.devcurrent, "value")
        vfocus = self.client.getDeviceParam(self.devfocus, "value")

        vvoltage_r = self.client.getDeviceParam(self.devvoltage_r, "value")
        vcurrent_r = self.client.getDeviceParam(self.devcurrent_r, "value")

        vvacuum = self.client.getDeviceParam(self.devvacuum, "value")
        vtemperature = self.client.getDeviceParam(self.devtemperature, "value")

        # Write parameter values.
        self.bmodel.setText(f"Model: {vmodel}")
        self.bstatus.setText(f"Status: {vstatus}")
        self.bbeam_align.setText(f"Beam Alignment Status: {vbeam_align}")
        self.binterlock.setText(f"Interlock Status: {vinterlock}")
        self.bvacuum.setText(f"Vacuum Level Check: {vvacuum}")
        self.btemperature.setText(f"Temperature Check: {vtemperature} C")
        self.bwvoltage.setText(f"{vvoltage}")
        self.brvoltage.setText(f"{vvoltage_r}")
        self.bwcurrent.setText(f"{vcurrent}")
        self.brcurrent.setText(f"{vcurrent_r}")
        self.bwfocus.setText(f"{vfocus}")

        self.xray()
        # self.align_x()
        # self.align_y()

        # Click buttons for X-ray.
        self.bxray.clicked.connect(self.xray)
        self.bwarmup.clicked.connect(self.warmup)
        self.breset.clicked.connect(self.reset)

        self.balign_all.clicked.connect(self.align_beam)
        self.balign_all.clicked.connect(self.align_all)
        self.balign_all.clicked.connect(self.align_stop)

        # Change values.
        self.bwvoltage.returnPressed.connect(self.voltage)
        self.bwcurrent.returnPressed.connect(self.current)
        self.bwfocus.returnPressed.connect(self.focus)
        self.bwalign_x.returnPressed.connect(self.align_x)
        self.bwalign_y.returnPressed.connect(self.align_y)

        # Buttons for detector.
        self.bstart.clicked.connect(self.start)
        self.bstop.clicked.connect(self.stop)
        self.bwacquire_time.returnPressed.connect(self.acquire_time)
        self.bwacquire_period.returnPressed.connect(self.acquire_period)


    def xray(self):
        test = self.client.getDeviceParam(self.devxray, "value")
        if test == "XOF":
            self.exec_command(f"move(xray, 'XON')")
            self.bxray.setText('X-ray ON')
        elif test == "XON":
            self.exec_command(f"move(xray, 'XOF')")
            self.bxray.setText('X-ray OFF')

    def warmup(self):
        self.exec_command(f"move(warmup, '')")

    def reset(self):
        self.exec_command(f"move(reset, '')")

    def voltage(self):
        value = self.bwvoltage.text()
        self.exec_command(f"move(voltage, {value})")

    def current(self):
        value = self.bwcurrent.text()
        self.exec_command(f"move(current, {value})")

    def focus(self): # will not finish due to no focus_r most likely
        value = self.bwfocus.text()
        self.exec_command(f"move(focus, {value})")

    def align_x(self): # will not finish due to no align_x_r most likely
            value = self.bwalign_x.text()
            self.exec_command(f"move(align_x, {value})")

    def align_y(self): # will not finish due to no align_y_r most likely
            value = self.bwalign_y.text()
            self.exec_command(f"move(align_y, {value})")

    def align_beam(self):
         self.exec_command(f"move(align_beam, '')")

    def align_all(self):
        self.exec_command(f"move(align_all, '')")

    def align_stop(self):
        self.exec_command(f"move(align_stop, '')")

    def start(self):
        self.exec_command(f"SetDetectors({self.devcollector})")
        self.exec_command(f"{self.devcamera}.start()")

    def stop(self):
        self.exec_command(f"stop({self.devcamera})")

    def acquire_time(self):
        value = self.bwacquire_time.text()
        self.exec_command(f"set({self.devcamera}, 'acquiretime', {value})")

    def acquire_period(self):
        value = self.bwacquire_period.text()
        self.exec_command(f"set({self.devcamera}, 'acquireperiod', {value})")


    # Setup commands.
    def get_info(self):
        if self._is_live():
            self.load_data()

    def _is_live(self):
        check = self.client.getDeviceList()
        # name returns as a list if something exists
        if check != []:
            return True
        return False

    def on_client_setup(self):
        self.get_info()


    # Other commands.
    def exec_command(self, command):
        self._exec_reqid = self.client.run(command)

    @pyqtSlot()
    def on_butStart_pressed(self):
        target = []
        for axis in self.qtObj:
            target.append(self.qtObj[axis]["newVal"].value())
        self.exec_command(f"move({self.devname}, ({target}))")