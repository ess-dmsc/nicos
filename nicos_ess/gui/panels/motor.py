from nicos.clients.gui.utils import dialogFromUi, loadUi
from nicos.guisupport.qt import (
    QCursor,
    QDialog,
    QDoubleValidator,
    QInputDialog,
    QMenu,
    QMessageBox,
    QSizePolicy,
    QSpacerItem,
    QTreeWidgetItem,
    pyqtSignal,
    pyqtSlot,
    sip,
)
from nicos.guisupport.typedvalue import (
    ComboWidget,
    DeviceParamEdit,
    DeviceValueEdit,
)
from nicos.protocols.cache import cache_load
from nicos.utils import findResource
from nicos_ess.gui.dialogs.homing_check import HomingCheckDialog
from nicos_ess.gui.panels.utils import (
    attach_status_resources,
    convert_limit_to_string,
    setBackgroundBrush,
    setForegroundBrush,
)


class MotorDialog(QDialog):
    """Dialog opened to control and view details for one device."""

    closed = pyqtSignal(object)

    def __init__(self, parent, devname, devinfo, devitem, log, expert):
        QDialog.__init__(self, parent)
        attach_status_resources(self)
        loadUi(self, findResource("nicos_ess/gui/panels/ui_files/motor.ui"))
        self.log = log

        self.col_index = {
            "NAME": 0,
            "VALUE": 1,
            "TARGET": 2,
            "STATUS": 3,
        }

        self.device_panel = parent
        self.client = parent.client
        self.devname = devname
        self.devinfo = devinfo
        self.devitem = devitem
        self.paramItems = {}
        self._reinit()

        self.txt_target.setFocus()

        if expert:
            self.paramGroup.setVisible(True)
        else:
            self.paramGroup.setVisible(False)
            spacer = QSpacerItem(
                0, 0, QSizePolicy.Policy.Minimum, QSizePolicy.Policy.Expanding
            )
            self.main_layout.insertItem(self.main_layout.count() - 2, spacer)
        sz = self.size()
        sz.setHeight(self.sizeHint().height())
        self.resize(sz)

    def _reinit(self):
        if sip.isdeleted(self.devitem):
            # The item we're controlling has been removed from the list (e.g.
            # due to client reconnect), get it again.
            self.devitem = self.device_panel._devitems.get(self.devname.lower())
            # No such device anymore...
            if self.devitem is None:
                self.close()
                return

        self.update_params()
        params = self.paramvalues

        self.deviceName.setText("Device: %s" % self.devname)
        self.setWindowTitle("Control %s" % self.devname)

        # show "Set alias" group box if it is an alias device
        # if "alias" in params:
        #     if params["alias"]:
        #         self.deviceName.setText(
        #             self.deviceName.text() + " (alias for %s)" % params["alias"]
        #         )
        #     alias_config = self.client.eval("session.alias_config", {})
        #     self.aliasTarget = QComboBox(self)
        #     self.aliasTarget.setEditable(True)
        #     if self.devname in alias_config:
        #         items = [t[0] for t in alias_config[self.devname]]
        #         self.aliasTarget.addItems(items)
        #         if params["alias"] in items:
        #             self.aliasTarget.setCurrentIndex(items.index(params["alias"]))
        #     self.targetLayoutAlias.takeAt(1).widget().deleteLater()
        #     self.targetLayoutAlias.insertWidget(1, self.aliasTarget)
        #     if self.client.viewonly:
        #         self.setAliasBtn.setEnabled(False)
        # else:
        #     self.aliasGroup.setVisible(False)

        double_validator = QDoubleValidator()
        self.txt_target.setValidator(double_validator)
        self.txt_rmove.setValidator(double_validator)

        # Populate value fields
        if params.get("description"):
            self.description.setText(params["description"])
        else:
            self.description.setVisible(False)

        self.txt_value.setText(self.devitem.text(self.col_index["VALUE"]))
        self.txt_status.setText(self.devitem.text(self.col_index["STATUS"]))
        self.statusimage.setPixmap(self.devitem.icon(0).pixmap(16, 16))
        setForegroundBrush(
            self.txt_status, self.devitem.foreground(self.col_index["STATUS"])
        )
        setBackgroundBrush(
            self.txt_status, self.devitem.background(self.col_index["STATUS"])
        )

        self.txt_user_limits_from.setText(
            convert_limit_to_string(params["userlimits"][0], params["fmtstr"])
        )
        self.txt_user_limits_to.setText(
            convert_limit_to_string(params["userlimits"][1], params["fmtstr"])
        )

        self.txt_hw_limits_from.setText(
            convert_limit_to_string(params["abslimits"][0], params["fmtstr"])
        )
        self.txt_hw_limits_to.setText(
            convert_limit_to_string(params["abslimits"][1], params["fmtstr"])
        )

        self.update_units(params["unit"])

        # TODO: use helpers from above?
        self.txt_target.setText(str(params["target"]))
        self.txt_speed.setText(str(params["speed"]))
        self.txt_offset.setText(str(params["offset"]))

        # add a menu for the "More" button
        menu = QMenu(self)
        menu.addAction(self.actionHome)
        # TODO: what does set position do?
        # if "nicos.devices.abstract.Coder" in classes:
        #     menu.addAction(self.actionSetPosition)
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
        classes = set(self.devinfo.classes or ())

        # trigger parameter poll
        self.client.eval("%s.pollParams()" % self.devname, None)

        # now get all cache keys pertaining to the device and set the
        # properties we want
        params = self.client.getDeviceParams(self.devname)
        self.paraminfo = self.client.getDeviceParamInfo(self.devname)
        self.paramvalues = dict(params)
        # Cache updates for "classes" may lag behind the dialog opening.
        # Use cache value if present, otherwise query the live device classes
        # so Moveable/Readable controls are initialized reliably.
        param_classes = params.get("classes")
        if isinstance(param_classes, str):
            classes = {param_classes}
        elif param_classes:
            classes = set(param_classes)
        elif not classes:
            live_classes = self.client.eval(
                "session.getDevice(%r).classes" % self.devname, []
            )
            classes = set(live_classes or ())
        self.devinfo.classes = classes

        # put parameter values in the list widget
        self.paramItems.clear()
        self.paramList.clear()
        for key, value in sorted(params.items()):
            if self.paraminfo.get(key):
                # normally, show only userparams, except in expert mode
                is_userparam = self.paraminfo[key]["userparam"]
                if is_userparam or self.device_panel._show_lowlevel:
                    self.paramItems[key] = item = QTreeWidgetItem(
                        self.paramList, [key, str(value)]
                    )
                    # display non-userparams in grey italics, like lowlevel
                    # devices in the device list
                    if not is_userparam:
                        item.setFont(
                            self.col_index["NAME"], self.device_panel.lowlevelFont[True]
                        )
                        item.setForeground(
                            self.col_index["NAME"],
                            self.device_panel.lowlevelBrush[True],
                        )

        # check how to refer to the device in commands: if it is not in the
        # namespace, we need to use quotes
        self.devrepr = (
            repr(self.devname)
            if "namespace" not in params.get("visibility", ("namespace",))
            else self.devname
        )

    def rmove(self, direction):
        step_size = self.txt_rmove.text()
        if step_size:
            target = self.devinfo.value + direction * float(step_size)
            self.device_panel.exec_command("maw(%s, %r)" % (self.devrepr, target))

    def move(self):
        target = self.txt_target.text()
        if target:
            self.device_panel.exec_command("move(%s, %r)" % (self.devrepr, target))

    def reset(self):
        self.device_panel.exec_command("reset(%s)" % self.devrepr)

    def stop(self):
        self.device_panel.exec_command("stop(%s)" % self.devrepr, immediate=True)

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

    def on_paramList_customContextMenuRequested(self, pos):
        item = self.paramList.itemAt(pos)
        if not item:
            return

        menu = QMenu(self)
        refreshAction = menu.addAction("Refresh")
        menu.addAction("Refresh all")

        # QCursor.pos is more reliable then the given pos
        action = menu.exec(QCursor.pos())

        if action:
            cmd = "session.getDevice(%r).pollParams(volatile_only=False%s)" % (
                self.devname,
                ", param_list=[%r]" % item.text(0) if action == refreshAction else "",
            )
            # poll even non volatile parameter as requested explicitly
            self.client.eval(cmd, None)

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
            self.device_panel.exec_command("resetlimits(%s)" % self.devrepr)
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
        self.device_panel.exec_command(
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
    def on_actionAdjustOffset_triggered(self):
        val = self._get_new_value(
            "Adjust NICOS offset", "Adjust NICOS offset of %s:" % self.devname
        )
        if val is not None:
            self.device_panel.exec_command("adjust(%s, %r)" % (self.devrepr, val))

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
            self.device_panel.exec_command(cmd)

    @pyqtSlot()
    def on_actionHome_triggered(self):
        home_warning_msg = self.paramvalues.get("home_warning_msg", None)
        if home_warning_msg:
            qwindow = HomingCheckDialog(home_warning_msg)
            if not qwindow.exec():
                return

        self.device_panel.exec_command("home(%s)" % self.devrepr)

    @pyqtSlot()
    def on_actionFix_triggered(self):
        reason, ok = QInputDialog.getText(
            self, "Fix", "Please enter the reason for fixing %s:" % self.devname
        )
        if not ok:
            return
        self.device_panel.exec_command("fix(%s, %r)" % (self.devrepr, reason))

    @pyqtSlot()
    def on_actionRelease_triggered(self):
        self.device_panel.exec_command("release(%s)" % self.devrepr)

    @pyqtSlot()
    def on_actionEnable_triggered(self):
        self.device_panel.exec_command("enable(%s)" % self.devrepr)

    @pyqtSlot()
    def on_actionDisable_triggered(self):
        self.device_panel.exec_command("disable(%s)" % self.devrepr)

    @pyqtSlot()
    def on_setAliasBtn_clicked(self):
        self.device_panel.exec_command(
            'set(%s, "alias", %r)' % (self.devrepr, self.aliasTarget.currentText())
        )

    @pyqtSlot()
    def on_btn_close_clicked(self):
        self.closed.emit(self.devname.lower())

    def closeEvent(self, event):
        event.accept()
        self.closed.emit(self.devname.lower())

    def on_paramList_itemClicked(self, item):
        pname = item.text(self.col_index["NAME"])
        self.editParam(pname)

    def editParam(self, pname):
        if not self.paraminfo[pname]["settable"] or self.client.viewonly:
            return
        mainunit = self.paramvalues.get("unit", "main")
        punit = (self.paraminfo[pname]["unit"] or "").replace("main", mainunit)

        dlg = dialogFromUi(
            self, findResource("nicos_ess/gui/panels/ui_files/devices_param.ui")
        )

        if pname in ("temperature", "electric_field", "magnetic_field"):
            params = self.client.getDeviceParams(self.devname)
            curr_value = params[pname]
            catitems = self.device_panel._catitems
            system_devs = [
                catitems[c].child(i).text(0)
                for c in catitems
                if catitems[c].text(0) == "system"
                for i in range(catitems[c].childCount())
            ]
            non_system_devs = [
                d for d in self.client.getDeviceList() if d not in system_devs
            ]
            if curr_value not in non_system_devs:
                curr_value = ""
            dlg.target = ComboWidget(self, non_system_devs, curr_value)
        else:
            dlg.target = DeviceParamEdit(self, dev=self.devname, param=pname)
            dlg.target.setClient(self.client)
        dlg.paramName.setText("Parameter: %s.%s" % (self.devname, pname))
        dlg.paramDesc.setText(self.paraminfo[pname]["description"])
        dlg.paramValue.setText(str(self.paramvalues[pname]) + " " + punit)
        dlg.targetLayout.addWidget(dlg.target)
        dlg.resize(dlg.sizeHint())
        dlg.target.setFocus()
        if dlg.exec() != QDialog.DialogCode.Accepted:
            return
        try:
            new_value = dlg.target.getValue()
        except ValueError:
            self.log.exception("invalid value for typed value")
            # shouldn't happen, but if it does, at least give an indication that
            # something went wrong
            QMessageBox.warning(
                self, "Error", "The entered value is invalid for this parameter."
            )
            return
        if self.devrepr == self.devname:
            self.device_panel.exec_command(
                "%s.%s = %r" % (self.devname, pname, new_value)
            )
        else:
            self.device_panel.exec_command(
                "set(%s, %r, %r)" % (self.devrepr, pname, new_value)
            )

    def update_units(self, value):
        self.txt_value.setText(self.devitem.text(self.col_index["VALUE"]))
        self.txt_target_units.setText(value)
        self.txt_rmove_units.setText(value)
        self.txt_speed_units.setText(f"{value}/s" if value else "")

    def update_current_value(self, value):
        pass

    @pyqtSlot()
    def on_btn_history_clicked(self):
        self.device_panel.plot_history(self.devname)

    def set_fixed(self, fixed):
        self.btn_move.setEnabled(not fixed)
        self.btn_move.setText("(fixed)" if fixed else "Move")
        self.txt_target.setEnabled(not fixed)
        self.btn_rmove_minus.setEnabled(not fixed)
        self.btn_rmove_plus.setEnabled(not fixed)
        self.txt_rmove.setEnabled(not fixed)

    def on_cache_params(self, subkey, value):
        if subkey not in self.paramItems:
            return
        if not value:
            return
        value = cache_load(value)
        self.paramvalues[subkey] = value
        self.paramItems[subkey].setText(self.col_index["VALUE"], str(value))

    def on_cache(self, time, subkey, op, value):
        if time < self.devinfo.valtime:
            return

        if subkey == "value":
            fmted = self.devinfo.fmtValUnit()
            self.txt_value.setText(fmted)
        elif subkey == "status":
            status = self.devinfo.status
            self.txt_status.setText(status[1])
            self.statusimage.setPixmap(self.statusIcon[status[0]].pixmap(16, 16))
            setForegroundBrush(self.txt_status, self.fgBrush[status[0]])
            setBackgroundBrush(self.txt_status, self.bgBrush[status[0]])
        elif subkey == "fixed":
            fixed = self.devinfo.fixed
            self.set_fixed(fixed)
        elif subkey == "userlimits":
            if not value:
                return
            value = cache_load(value)
            self.txt_user_limits_from.setText(
                convert_limit_to_string(value[0], self.devinfo.fmtstr)
            )
            self.txt_user_limits_to.setText(
                convert_limit_to_string(value[1], self.devinfo.fmtstr)
            )
        elif subkey == "abslimits":
            if not value:
                return
            value = cache_load(value)
            self.txt_hw_limits_from.setText(
                convert_limit_to_string(value[0], self.devinfo.fmtstr)
            )
            self.txt_hw_limits_to.setText(
                convert_limit_to_string(value[1], self.devinfo.fmtstr)
            )
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
            self.txt_offset.setText(str(cache_load(value)))
