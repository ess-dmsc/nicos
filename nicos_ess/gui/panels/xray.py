"""NICOS X-ray panel."""

from nicos.clients.gui.panels import Panel
from nicos.clients.gui.utils import loadUi
from nicos.utils import findResource
from nicos_ess.gui.panels.live_pyqt import LiveDataPanel
from nicos.guisupport.qt import QSpinBox, QTimer
from PyQt5.QtCore import Qt

class XrayPanel(Panel):
    def __init__(self, parent, client, options):
        Panel.__init__(self, parent, client, options)
        loadUi(self, findResource("nicos_ess/ymir/gui/xray.ui"))

        # Get devices.
        self.devstatus = options.get("status")
        self.devbeam_align = options.get("beam_align")
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
        self.devsource_motor = options.get("source_motor")
        self.devflatpanel_motor = options.get("flatpanel_motor")

        # Create and place detector image.
        self.panel = LiveDataPanel(parent, client, options) #can also use MultiLiveDataPanel
        self.panel.update_widget_to_show(True) #shows 2D-image
        self.place_panel.addWidget(self.panel)

        # Put items in menus.
        self.create_filter_menu()
        self.create_image_mode_menu()

        # Disable scrolling values for voltage and current. 
        # Do the same for DoubleSpinBoxes or specific DoubleSpinBoxes if you wish.
        opts = Qt.FindChildrenRecursively
        spinboxes = self.findChildren(QSpinBox, options=opts)
        for box in spinboxes:
            box.wheelEvent = lambda *event: None

        self.timer = QTimer(self) #for the blinking warmup light

        # Start client.
        client.setup.connect(self.on_client_setup) #keeps running until setup is ready
        client.cache.connect(self.on_client_cache) #update position and status info


    def _is_live(self):
        check = self.client.getDeviceList()
        # name returns as a non-empty list if something exists
        if check != []:
            return True
        return False

    def on_client_setup(self):
        if self._is_live():
            self.load_data()

    def on_client_cache(self, data):
        (time, key, op, value) = data
        if "/" not in key:
            return
        devname, pname = key.split("/")
        # if devname != "session":
        #     print(devname, pname, value)

        # Update position for source motor and flatpanel motor.
        if devname == self.devsource_motor and pname == "value":
            self.brsource_motor.setText(str(round(float(value), 2)))
        elif devname == self.devflatpanel_motor and pname == "value":
            self.brflatpanel_motor.setText(str(round(float(value), 2)))

        # Update status.
        elif devname == self.devstatus and pname == "value":
            self.status_value = self.client.getDeviceParam(self.devstatus, "value")
            if pname != self.status_value:
                self.status_value = pname
                self.status()

    def exec_command(self, command):
        self._exec_reqid = self.client.run(command)


    def load_data(self):
        # Read parameter values.
        vbeam_align = self.client.getDeviceParam(self.devbeam_align, "value")
        vxray = self.client.getDeviceParam(self.devxray, "value")

        vvoltage = self.client.getDeviceParam(self.devvoltage, "value")
        vcurrent = self.client.getDeviceParam(self.devcurrent, "value")
        vfocus = self.client.getDeviceParam(self.devfocus, "value")

        vvoltage_r = self.client.getDeviceParam(self.devvoltage_r, "value")
        vcurrent_r = self.client.getDeviceParam(self.devcurrent_r, "value")

        vvacuum = self.client.getDeviceParam(self.devvacuum, "value")
        vtemperature = self.client.getDeviceParam(self.devtemperature, "value")

        vacquire_time = self.client.getDeviceParam(self.devcamera, "acquiretime")
        vacquire_period = self.client.getDeviceParam(self.devcamera, "acquireperiod")
        vnum_images = self.client.getDeviceParam(self.devcamera, "numimages")
        vimage_mode = self.client.getDeviceParam(self.devcamera, "imagemode")

        vsource_motor = self.client.getDeviceParam(self.devsource_motor, "value")
        vflatpanel_motor = self.client.getDeviceParam(self.devflatpanel_motor, "value")

        # Write parameter values.
        self.brbeam_align.setText(vbeam_align)
        self.brvacuum.setText(str(vvacuum))
        self.brtemperature.setText(str(vtemperature))
        self.bwfocus.setValue(vfocus)

        if vxray == "XOF":
            self.xray_info.setText("X-ray OFF")
            self.bxray.setText("Turn ON")
        elif vxray == "XON":
            self.xray_info.setText("X-ray ON")
            self.bxray.setText("Turn OFF")

        self.bwvoltage.setValue(vvoltage)
        self.brvoltage.setText(str(vvoltage_r))
        voltage_percentage = int(round(vvoltage-20)/280*100)
        self.progress_voltage.setValue(voltage_percentage)
        
        self.bwcurrent.setValue(vcurrent)
        self.brcurrent.setText(str(vcurrent_r))
        current_percentage = int(round(vcurrent/10))
        self.progress_current.setValue(current_percentage)

        self.bwacquire_time.setValue(vacquire_time)
        self.bracquire_time.setText(str(vacquire_time))
        self.bwacquire_period.setValue(vacquire_period)
        self.bracquire_period.setText(str(vacquire_period))
        self.bwnum_images.setValue(vnum_images)
        self.brnum_images.setText(str(vnum_images))
        self.image_mode_menu.setCurrentText(vimage_mode)

        self.bwsource_motor.setValue(vsource_motor)
        self.bwflatpanel_motor.setValue(vflatpanel_motor)

        self.status_value = self.client.getDeviceParam(self.devstatus, "value")
        self.status()
        self.update_power()

        # Set start values.
        self.exec_command(f"move(filter_menu, 'No filter')") # can remove if you want to remember filter choice between sessions 
                                                             # (but then you have to add reading and setting the choice of filter
                                                             #  in this function, like with imagemode)
        self.exec_command(f"SetDetectors({self.devcollector})")


    def status(self):
        stylesheet = "; border-radius: 20px; border: 3px solid black;"

        if self.status_value != "WARMUP":
            if self.timer.isActive():
                self.timer.stop()
        
        if self.status_value == "NOT READY":
            self.brstatus.setText("ERROR")
            self.warmup_info.setText("Not warmed up")
            self.status_light.setStyleSheet("background-color: red" + stylesheet)
        elif self.status_value == "WARMUP YET":
            self.brstatus.setText("READY FOR WARMUP")
            self.warmup_info.setText("Not warmed up")
            self.status_light.setStyleSheet("background-color: gray" + stylesheet)
        elif self.status_value == "WARMUP":
            self.brstatus.setText(self.status_value)
            self.warmup_info.setText("Warming up")
            self.color = 0
            self.timer.timeout.connect(self.blink)
            self.timer.start(500)
        elif self.status_value == "STANDBY":
            self.brstatus.setText("READY FOR X-RAYS")
            self.warmup_info.setText("Warmup complete")
            self.status_light.setStyleSheet("background-color: orange" + stylesheet)
        elif self.status_value == "XON":
            self.brstatus.setText("X-Ray ON")
            self.warmup_info.setText("Warmup complete")
            self.status_light.setStyleSheet("background-color: limegreen" + stylesheet)
        elif self.status_value == "OVER":
            self.brstatus.setText("OVERLOAD")
            self.warmup_info.setText("Overload")
            self.status_light.setStyleSheet("background-color: red" + stylesheet)

    def blink(self):
        stylesheet = "; border-radius: 20px; border: 3px solid black;"
        if self.color == 0:
            self.status_light.setStyleSheet("background-color: orange" + stylesheet)
            self.color = 1
        else:
            self.status_light.setStyleSheet("background-color: gray" + stylesheet)
            self.color = 0

    # Commands to control the devices.
    def on_bxray_pressed(self):
        value = self.client.getDeviceParam(self.devxray, "value")
        if value == "XOF":
            self.exec_command(f"move(xray, 'XON')")
            self.xray_info.setText('X-ray ON')
            self.bxray.setText('Turn OFF')
        elif value == "XON":
            self.exec_command(f"move(xray, 'XOF')")
            self.xray_info.setText('X-ray OFF')
            self.bxray.setText('Turn ON')

    def on_bwarmup_pressed(self):
        self.exec_command(f"move(warmup, '')")

    def on_breset_pressed(self):
        self.exec_command(f"move(reset, '')")

    def on_bwvoltage_editingFinished(self):
        curvalue = self.client.getDeviceParam(self.devvoltage, "value")
        newvalue = self.bwvoltage.value()
        if curvalue != newvalue:
            self.exec_command(f"move(voltage, {newvalue})")
            percentage = int(round(newvalue-20)/280*100)
            self.progress_voltage.setValue(percentage) #change to read-value when x-ray is working
            self.update_power(voltage=newvalue)

    # When the voltage is 231 kV or more, the voltage can only take on values between 0 and 500 uA. Maybe add this limitation?
    def on_bwcurrent_editingFinished(self):
        curvalue = self.client.getDeviceParam(self.devcurrent, "value")
        newvalue = self.bwcurrent.value()
        if curvalue != newvalue:
            self.exec_command(f"move(current, {newvalue})")
            percentage = int(round(newvalue/10))
            self.progress_current.setValue(percentage) #change to read-value when x-ray is working
            self.update_power(current=newvalue)

    def update_power(self, voltage=-1, current=-1):
        # It doesn't have time to update the actual values if you just changed them before calling
        # on this function, so this ensures that the right value is called if it was just changed.
        # But this should also be event based from the EPICS side in the future.
        if voltage == -1:
            voltage = self.client.getDeviceParam(self.devvoltage, "value")
        if current == -1:
            current = self.client.getDeviceParam(self.devcurrent, "value")
        power = voltage * current * 10**(-3)
        self.brpower.setText(str(round(power)))
        percentage = int(round(power/230*100))
        self.progress_power.setValue(percentage)

    def on_bwfocus_editingFinished(self): # will not finish due to no focus_r most likely
        curvalue = self.client.getDeviceParam(self.devfocus, "value")
        newvalue = self.bwfocus.value()
        if curvalue != newvalue:
            self.exec_command(f"move(focus, {newvalue})")

    def on_bwalign_x_editingFinished(self): # will not finish due to no align_x_r most likely
        curvalue = self.client.getDeviceParam(self.devalign_x, "value")
        newvalue = self.bwalign_x.value()
        if curvalue != newvalue:
            self.exec_command(f"move(align_x, {newvalue})")

    def on_bwalign_y_editingFinished(self): # will not finish due to no align_y_r most likely
        curvalue = self.client.getDeviceParam(self.devalign_y, "value")
        newvalue = self.bwalign_y.value()
        if curvalue != newvalue:
            self.exec_command(f"move(align_y, {newvalue})")

    def on_balign_beam_pressed(self):
         self.exec_command(f"move(align_beam, '')")

    def on_balign_all_pressed(self):
        self.exec_command(f"move(align_all, '')")

    def on_balign_stop_pressed(self):
        self.exec_command(f"move(align_stop, '')")

    def on_bstart_pressed(self):
        self.exec_command(f"{self.devcamera}.start()")

    def on_bstop_pressed(self):
        self.exec_command(f"stop({self.devcamera})")

    def on_bwacquire_time_editingFinished(self):
        curvalue = self.client.getDeviceParam(self.devcamera, "acquiretime")
        newvalue = self.bwacquire_time.text()
        if curvalue != newvalue:
            self.exec_command(f"set({self.devcamera}, 'acquiretime', {newvalue})")
            self.bracquire_time.setText(str(newvalue))

    def on_bwacquire_period_editingFinished(self):
        curvalue = self.client.getDeviceParam(self.devcamera, "acquireperiod")
        newvalue = self.bwacquire_period.text()
        if curvalue != newvalue:
            self.exec_command(f"set({self.devcamera}, 'acquireperiod', {newvalue})")
            self.bracquire_period.setText(str(newvalue))

    def on_bwnum_images_editingFinished(self):
        curvalue = self.client.getDeviceParam(self.devcamera, "numimages")
        newvalue = self.bwnum_images.text()
        if curvalue != newvalue:
            self.exec_command(f"set({self.devcamera}, 'numimages', {newvalue})")
            self.brnum_images.setText(str(newvalue))

    # Placeholder motors.
    def on_bwsource_motor_editingFinished(self):
        curvalue = self.client.getDeviceParam(self.devsource_motor, "value")
        newvalue = self.bwsource_motor.value()
        if curvalue != newvalue:
            self.exec_command(f"move({self.devsource_motor}, {newvalue})")

    def on_bwflatpanel_motor_editingFinished(self):
        curvalue = self.client.getDeviceParam(self.devflatpanel_motor, "value")
        newvalue = self.bwflatpanel_motor.value()
        if curvalue != newvalue:
            self.exec_command(f"move({self.devflatpanel_motor}, {newvalue})")


    # Functions for the two menus (image mode and filter).
    def create_image_mode_menu(self):
        items = ["single", "multiple", "continuous"]
        self.image_mode_menu.addItems(items)
        self.image_mode_menu.currentTextChanged.connect(self.on_image_mode_changed)

    def create_filter_menu(self):
        items = ["No filter", "Al 1.2mm", "Fe 0.3mm", "Cu 0.35mm", "Cu0.35mm Fe0.3mm", "Cu 0.65mm"]
        self.filter_menu.addItems(items)
        self.filter_menu.currentTextChanged.connect(self.on_filter_changed)

    def on_image_mode_changed(self, selected_mode):
        self.exec_command(f"set({self.devcamera}, 'imagemode', '{selected_mode}')")

    def on_filter_changed(self, selected_filter):
        self.exec_command(f"move(filter_menu, '{selected_filter}')")