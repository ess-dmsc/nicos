from nicos.clients.gui.utils import dialogFromUi, loadUi
from nicos.guisupport.qt import (
    QDialog,
    QDoubleValidator,
    QInputDialog,
    QMenu,
    QMessageBox,
    QSizePolicy,
    QSpacerItem,
    pyqtSignal,
    pyqtSlot,
    sip,
)
from nicos.guisupport.typedvalue import (
    DeviceParamEdit,
    DeviceValueEdit,
)
from nicos.protocols.cache import cache_load
from nicos.utils import findResource
from nicos_ess.gui.dialogs.homing_check import HomingCheckDialog
from nicos_ess.gui.panels.parameters_table import ParametersTable
from nicos_ess.gui.panels.utils import (
    attach_status_resources,
    convert_limit_to_string,
    setBackgroundBrush,
    setForegroundBrush,
)


class MotorDialog(QDialog):
    """Dialog opened to control and view details for an EPIC motor device."""

    closed = pyqtSignal(object)

    def __init__(self, parent, devname, devinfo, devitem, log, expert):
        QDialog.__init__(self, parent)
        attach_status_resources(self)
        loadUi(self, findResource("nicos_ess/gui/panels/ui_files/motor.ui"))
        self.log = log

        # All executable commands go via the top-level devices panel
        self.devices_panel = parent
        self.client = parent.client
        self.devname = devname
        self.devinfo = devinfo
        self.devitem = devitem
        self.param_table = ParametersTable(
            parent, self.client, self.devname, self.devices_panel
        )

        self._reinit()

        self.txt_target.setFocus()

        if expert:
            self.main_layout.insertWidget(
                self.main_layout.count() - 1, self.param_table
            )
        else:
            spacer = QSpacerItem(
                0, 0, QSizePolicy.Policy.Minimum, QSizePolicy.Policy.Expanding
            )
            self.main_layout.insertItem(self.main_layout.count() - 1, spacer)
        sz = self.size()
        sz.setHeight(self.sizeHint().height())
        self.resize(sz)

    def _reinit(self):
        if sip.isdeleted(self.devitem):
            # The item we're controlling has been removed from the list (e.g.
            # due to client reconnect), get it again.
            self.devitem = self.devices_panel._devitems.get(self.devname.lower())
            # No such device anymore...
            if self.devitem is None:
                self.close()
                return

        self.update_params()
        params = self.paramvalues

        # check how to refer to the device in commands: if it is not in the
        # namespace, we need to use quotes
        self.devrepr = (
            repr(self.devname)
            if "namespace" not in params.get("visibility", ("namespace",))
            else self.devname
        )

        self.deviceName.setText("Device: %s" % self.devname)
        self.setWindowTitle("Control %s" % self.devname)

        double_validator = QDoubleValidator()
        self.txt_target.setValidator(double_validator)
        self.txt_rmove.setValidator(double_validator)

        # Populate value fields
        if params.get("description"):
            self.description.setText(params["description"])
        else:
            self.description.setVisible(False)

        self.update_value()
        self.update_status(self.devinfo.status[0], self.devinfo.status[1])
        self.update_user_limits(params["userlimits"])
        self.update_abs_limits(params["abslimits"])
        self.update_units(params["unit"])
        self.txt_target.setText(str(params["target"]))
        self.txt_speed.setText(str(params["speed"]))
        self.update_offset(params["offset"])

        # add a menu for the "More" button
        menu = QMenu(self)
        menu.addAction(self.actionHome)
        menu.addSeparator()
        menu.addAction(self.actionSetPosition)
        menu.addSeparator()
        menu.addAction(self.actionFix)
        menu.addAction(self.actionRelease)
        menu.addSeparator()
        menu.addAction(self.actionEnable)
        menu.addAction(self.actionDisable)
        self.btn_more.setMenu(menu)

        fixed = self.devinfo.fixed
        self.set_fixed(fixed)

    def update_params(self):
        # Trigger parameter poll
        self.client.eval("%s.pollParams()" % self.devname, None)

        # Get parameter information from daemon
        # paramvalues contains the name and the value.
        params = self.client.getDeviceParams(self.devname)
        self.paramvalues = dict(params)
        # paraminfo contains the name and all the metadata about the parameter.
        # E.g. whether it is a user parameter
        self.paraminfo = self.client.getDeviceParamInfo(self.devname)

        self.param_table.set_params(self.paramvalues, self.paraminfo)

    def rmove(self, direction):
        step_size = self.txt_rmove.text()
        if step_size:
            target = self.devinfo.value + direction * float(step_size)
            self.devices_panel.exec_command("maw(%s, %r)" % (self.devrepr, target))

    def move(self):
        target = self.txt_target.text()
        if target:
            self.devices_panel.exec_command("move(%s, %r)" % (self.devrepr, target))

    def reset(self):
        self.devices_panel.exec_command("reset(%s)" % self.devrepr)

    def stop(self):
        self.devices_panel.exec_command("stop(%s)" % self.devrepr, immediate=True)

    @pyqtSlot()
    def on_txt_target_returnPressed(self):
        self.move()

    @pyqtSlot()
    def on_btn_move_pressed(self):
        self.move()

    @pyqtSlot()
    def on_btn_rmove_minus_pressed(self):
        self.rmove(-1)

    @pyqtSlot()
    def on_btn_rmove_plus_pressed(self):
        self.rmove(1)

    @pyqtSlot()
    def on_btn_stop_pressed(self):
        self.stop()

    @pyqtSlot()
    def on_btn_set_limits_clicked(self):
        dlg = dialogFromUi(
            self, findResource("nicos_ess/gui/panels/ui_files/devices_limits.ui")
        )
        dlg.descLabel.setText("Adjust user limits of %s:" % self.devname)

        userlimits = self.client.getDeviceParam(self.devname, "userlimits")
        dlg.limitMin.setText(
            convert_limit_to_string(userlimits[0], self.devinfo.fmtstr)
        )
        dlg.limitMax.setText(
            convert_limit_to_string(userlimits[1], self.devinfo.fmtstr)
        )

        abslimits = self.client.getDeviceParam(self.devname, "abslimits")
        offset = self.client.getDeviceParam(self.devname, "offset")
        if offset is not None:
            abslimits = abslimits[0] - offset, abslimits[1] - offset
        dlg.limitMinAbs.setText(
            convert_limit_to_string(abslimits[0], self.devinfo.fmtstr)
        )
        dlg.limitMaxAbs.setText(
            convert_limit_to_string(abslimits[1], self.devinfo.fmtstr)
        )

        target = DeviceParamEdit(dlg, dev=self.devname, param="userlimits")
        target.setClient(self.client)

        def callback():
            self.devices_panel.exec_command("resetlimits(%s)" % self.devrepr)
            dlg.reject()

        dlg.btn_reset.clicked.connect(callback)
        dlg.targetLayout.addWidget(target)
        res = dlg.exec()
        if res != QDialog.DialogCode.Accepted:
            return
        newlimits = target.getValue()
        if newlimits[0] < abslimits[0] or newlimits[1] > abslimits[1]:
            QMessageBox.warning(
                self,
                "Error",
                "The entered limits are not within the absolute limits for the device.",
            )
            # retry
            self.on_actionSetLimits_triggered()
            return
        self.devices_panel.exec_command(
            'set(%s, "userlimits", %s)' % (self.devrepr, newlimits)
        )

    def _get_new_value(self, window_title, desc):
        dlg = dialogFromUi(
            self, findResource("nicos_ess/gui/panels/ui_files/devices_newpos.ui")
        )
        dlg.setWindowTitle(window_title)
        dlg.descLabel.setText(desc)
        dlg.oldValue.setText(self.txt_value.text())
        target = DeviceValueEdit(dlg, dev=self.devname)
        target.setClient(self.client)
        dlg.targetLayout.addWidget(target)
        target.setFocus()
        res = dlg.exec()
        if res != QDialog.DialogCode.Accepted:
            return None
        return target.getValue()

    @pyqtSlot()
    def on_btn_set_offset_clicked(self):
        val = self._get_new_value("Adjust offset", "Redefine current position of %s" % self.devname)
        if val is not None:
            self.devices_panel.exec_command("adjust(%s, %r)" % (self.devrepr, val))

    @pyqtSlot()
    def on_actionSetPosition_triggered(self):
        val = self._get_new_value(
            "Set hardware position", "Set hardware position of %s:" % self.devname
        )
        if val is not None:
            if self.devrepr != self.devname:
                cmd = "CreateDevice(%s); %s.setPosition(%r)" % (
                    self.devrepr,
                    self.devname,
                    val,
                )
            else:
                cmd = "%s.setPosition(%r)" % (self.devname, val)
            self.devices_panel.exec_command(cmd)

    @pyqtSlot()
    def on_actionHome_triggered(self):
        home_warning_msg = self.paramvalues.get("home_warning_msg", None)
        if home_warning_msg:
            qwindow = HomingCheckDialog(home_warning_msg)
            if not qwindow.exec():
                return

        self.devices_panel.exec_command("home(%s)" % self.devrepr)

    @pyqtSlot()
    def on_actionFix_triggered(self):
        reason, ok = QInputDialog.getText(
            self, "Fix", "Please enter the reason for fixing %s:" % self.devname
        )
        if not ok:
            return
        self.devices_panel.exec_command("fix(%s, %r)" % (self.devrepr, reason))

    @pyqtSlot()
    def on_actionRelease_triggered(self):
        self.devices_panel.exec_command("release(%s)" % self.devrepr)

    @pyqtSlot()
    def on_actionEnable_triggered(self):
        self.devices_panel.exec_command("enable(%s)" % self.devrepr)

    @pyqtSlot()
    def on_actionDisable_triggered(self):
        self.devices_panel.exec_command("disable(%s)" % self.devrepr)

    @pyqtSlot()
    def on_setAliasBtn_clicked(self):
        self.devices_panel.exec_command(
            'set(%s, "alias", %r)' % (self.devrepr, self.aliasTarget.currentText())
        )

    @pyqtSlot()
    def on_btn_close_clicked(self):
        self.closed.emit(self.devname.lower())

    def closeEvent(self, event):
        event.accept()
        self.closed.emit(self.devname.lower())

    def update_units(self, value):
        self.update_value()
        self.txt_target_units.setText(value)
        self.txt_rmove_units.setText(value)
        self.txt_speed_units.setText(f"{value}/s" if value else "")
        self.txt_offset_units.setText(value)
        self.txt_hw_limits_units.setText(value)
        self.txt_user_limits_units.setText(value)

    def update_offset(self, value):
        fmted = self.devinfo.fmtstr % value
        self.txt_offset.setText(fmted)

    def update_user_limits(self, limits):
        self.txt_user_limits_from.setText(
            convert_limit_to_string(limits[0], self.devinfo.fmtstr)
        )
        self.txt_user_limits_to.setText(
            convert_limit_to_string(limits[1], self.devinfo.fmtstr)
        )

    def update_abs_limits(self, limits):
        self.txt_hw_limits_from.setText(
            convert_limit_to_string(limits[0], self.devinfo.fmtstr)
        )
        self.txt_hw_limits_to.setText(
            convert_limit_to_string(limits[1], self.devinfo.fmtstr)
        )

    def update_status(self, status, message):
        self.txt_status.setText(message)
        self.statusimage.setPixmap(self.statusIcon[status].pixmap(16, 16))
        setForegroundBrush(self.txt_status, self.fgBrush[status])
        setBackgroundBrush(self.txt_status, self.bgBrush[status])

    def update_value(self):
        self.txt_value.setText(self.devinfo.fmtValUnit())

    @pyqtSlot()
    def on_btn_history_clicked(self):
        self.devices_panel.plot_history(self.devname)

    def set_fixed(self, fixed):
        self.btn_move.setEnabled(not fixed)
        self.btn_move.setText("(fixed)" if fixed else "Move")
        self.txt_target.setEnabled(not fixed)
        self.btn_rmove_minus.setEnabled(not fixed)
        self.btn_rmove_plus.setEnabled(not fixed)
        self.txt_rmove.setEnabled(not fixed)

    def on_cache_params(self, subkey, value):
        if subkey not in self.paramvalues:
            return
        if not value:
            return
        value = cache_load(value)
        self.paramvalues[subkey] = value
        self.param_table.update_param(subkey, str(value))

    def on_cache(self, time, subkey, op, value):
        if time < self.devinfo.valtime:
            return

        if subkey == "value":
            self.update_value()
        elif subkey == "status":
            status, message = self.devinfo.status
            self.update_status(status, message)
        elif subkey == "fixed":
            fixed = self.devinfo.fixed
            self.set_fixed(fixed)
        elif subkey == "userlimits":
            if not value:
                return
            value = cache_load(value)
            self.update_user_limits(value)
        elif subkey == "abslimits":
            if not value:
                return
            value = cache_load(value)
            self.update_abs_limits(value)
        elif subkey == "alias":
            if not value:
                return
            self._reinit()
        elif subkey == "unit":
            if not value:
                value = ""
            else:
                value = cache_load(value)
            self.update_units(value)
        elif subkey == "speed":
            if not value:
                return
            self.txt_speed.setText(str(cache_load(value)))
        elif subkey == "offset":
            if not value:
                return
            self.update_offset(cache_load(value))
