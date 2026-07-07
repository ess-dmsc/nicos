from nicos.clients.gui.utils import dialogFromUi
from nicos.guisupport.qt import (
    QCursor,
    QDialog,
    QGroupBox,
    QMenu,
    QMessageBox,
    QSizePolicy,
    Qt,
    QTreeWidget,
    QTreeWidgetItem,
    QVBoxLayout,
    QWidget,
)
from nicos.utils import findResource
from nicos_ess.gui.panels.utils import (
    attach_status_resources,
)


class ParametersTable(QWidget):
    def __init__(self, parent, client, devname, devices_panel):
        QWidget.__init__(self, parent)
        attach_status_resources(self)

        self.client = client
        self.devname = devname
        self.devices_panel = devices_panel

        self.paramItems = {}
        self.param_info = {}
        self.param_values = {}

        layout = QVBoxLayout()
        group_box = QGroupBox("Parameters")
        sublayout = QVBoxLayout()

        self.tree_widget = QTreeWidget(parent)
        self.tree_widget.setColumnCount(2)
        self.tree_widget.setHeaderLabels(["Name", "Value"])
        self.tree_widget.setRootIsDecorated(False)
        self.tree_widget.itemClicked.connect(self.edit_param)
        self.tree_widget.setContextMenuPolicy(Qt.ContextMenuPolicy.CustomContextMenu)
        self.tree_widget.customContextMenuRequested.connect(self.on_context_menu)

        sublayout.addWidget(self.tree_widget)
        group_box.setLayout(sublayout)
        layout.addWidget(group_box)

        self.setLayout(layout)
        self.setSizePolicy(
            QSizePolicy.Policy.MinimumExpanding,
            QSizePolicy.Policy.MinimumExpanding,
        )

    def set_params(self, params, param_info, show_lowlevel=True):
        self.param_values = params
        self.param_info = param_info

        self.paramItems.clear()
        self.tree_widget.clear()

        for key, value in sorted(params.items()):
            if param_info.get(key):
                # normally, show only userparams, except in expert mode
                is_userparam = param_info[key]["userparam"]
                if is_userparam or show_lowlevel:
                    self.paramItems[key] = item = QTreeWidgetItem(
                        self.tree_widget, [key, str(value)]
                    )
                    # display non-userparams in grey italics
                    if not is_userparam:
                        item.setFont(0, self.lowlevelFont[True])
                        item.setForeground(
                            0,
                            self.lowlevelBrush[True],
                        )

    def update_param(self, name, value):
        if name in self.paramItems:
            self.paramItems[name].setText(1, str(value))

    def edit_param(self, item):
        pname = item.text(0)

        if not self.param_info[pname]["settable"] or self.client.viewonly:
            return

        mainunit = self.param_values.get("unit", "main")
        punit = (self.param_info[pname]["unit"] or "").replace("main", mainunit)

        dlg = dialogFromUi(
            self, findResource("nicos_ess/gui/panels/ui_files/devices_param.ui")
        )

        if pname in ("temperature", "electric_field", "magnetic_field"):
            params = self.client.getDeviceParams(self.devname)
            curr_value = params[pname]
            catitems = self.devices_panel._catitems
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
        dlg.paramDesc.setText(self.param_info[pname]["description"])
        dlg.paramValue.setText(str(self.param_values[pname]) + " " + punit)
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

        self.devices_panel.exec_command("%s.%s = %r" % (self.devname, pname, new_value))

    def on_context_menu(self, pos):
        item = self.tree_widget.itemAt(pos)
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
