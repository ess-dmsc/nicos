#  -*- coding: utf-8 -*-
# *****************************************************************************
# NICOS, the Networked Instrument Control System of the MLZ
# Copyright (c) 2009-2021 by the NICOS contributors (see AUTHORS)
#
# This program is free software; you can redistribute it and/or modify it under
# the terms of the GNU General Public License as published by the Free Software
# Foundation; either version 2 of the License, or (at your option) any later
# version.
#
# This program is distributed in the hope that it will be useful, but WITHOUT
# ANY WARRANTY; without even the implied warranty of MERCHANTABILITY or FITNESS
# FOR A PARTICULAR PURPOSE.  See the GNU General Public License for more
# details.
#
# You should have received a copy of the GNU General Public License along with
# this program; if not, write to the Free Software Foundation, Inc.,
# 59 Temple Place, Suite 330, Boston, MA  02111-1307  USA
#
# Module authors:
#   AÜC Hardal <umit.hardal@ess.eu>
#
# *****************************************************************************

"""LoKI Experiment Configuration dialog."""

from nicos.clients.gui.utils import loadUi
from nicos.guisupport.qt import QMessageBox, Qt, pyqtSlot
from nicos.utils import findResource

from nicos_ess.loki.gui.loki_panel import LokiPanelBase
from nicos_ess.loki.gui.loki_sample_changers import ThermoCellHolderSettings
from nicos_ess.utilities.validators import DoubleValidator

DEVICES = ('InstrumentSettings',)
SAMPLE_CHANGERS = ('Thermostated Cell Holder',)
INST_SET_KEYS = ('x', 'y', 'width', 'height', 'offset')


class LokiExperimentPanel(LokiPanelBase):
    panelName = 'LoKI Instrument Setup'

    def __init__(self, parent, client, options):
        LokiPanelBase.__init__(self, parent, client, options)
        self.parent = parent
        self.options = options
        loadUi(self, findResource('nicos_ess/loki/gui/ui_files/exp_config.ui'))

        self.holder_info = options.get('holder_info', [])
        self.instrument = options.get('instrument', 'loki')

        self.editable_settings = [
            self.apXBox, self.apYBox, self.apWBox,
            self.apHBox, self.offsetBox
        ]

        self.initialise_connection_status_listeners()
        self.initialise_markups()

        self.envComboBox.addItems([_changer for _changer in SAMPLE_CHANGERS])
        # Start with a "no item", ie, empty selection.
        self.envComboBox.setCurrentIndex(-1)

        self.descriptionGroupBox.setVisible(False)
        self.settingsGroupBox.setVisible(False)

        self.envComboBox.activated.connect(self._activate_environment_settings)

        # Listen to changes in Aperture and Detector Offset values
        self.listen_instrument_settings()

        # Disable apply buttons in both settings until an action taken by the
        # user.
        self.sampleSetApply.setEnabled(False)
        self.instSetApply.setEnabled(False)

        # Labels that will show up when a value change to show currently cached.
        self.currentValueLabels = [
            self.posXCurrent, self.posYCurrent, self.widthCurrent,
            self.heightCurrent, self.offsetCurrent
        ]

        self._disable_current_value_labels()

    def on_client_connected(self):
        LokiPanelBase.on_client_connected(self)
        self._set_cached_values_to_ui()
        self.initialise_validators()

    def on_client_disconnected(self):
        LokiPanelBase.on_client_disconnected(self)
        self.initialise_markups()

    def setViewOnly(self, viewonly):
        self.sampleSetGroupBox.setEnabled(not viewonly)
        self.instSetGroupBox.setEnabled(not viewonly)

    def initialise_markups(self):
        for box in self.editable_settings:
            box.clear()
            box.setAlignment(Qt.AlignRight)
            # The validator should be reset upon disconnection from the server.
            # This is due to false behaviour of QT when reconnected, ie, the
            # validator fails (does not initialise) until a valid value entered.
            box.setValidator(None)
            box.setPlaceholderText('1.0')

    def initialise_validators(self):
        _validator_values = {  # in units of mm
            'bottom': 0.0,
            'top': 1000.0,
            'decimal': 5,
        }
        validator = DoubleValidator(**_validator_values)
        for box in self.editable_settings:
            box.setValidator(validator)

    def listen_instrument_settings(self):
        for box in self.editable_settings:
            box.textChanged.connect(self._instrument_settings_changed)

        for box in self.editable_settings:
            box.textEdited.connect(self._inform_current_instrument_values)

    def _instrument_settings_changed(self):
        self.instSetApply.setEnabled(True)

    def _inform_current_instrument_values(self):
        cached_values = self._get_cached_values_of_instrument_settings()
        ui_values = self._get_current_values_of_instrument_settings()
        for index, value in enumerate(ui_values):
            if value == '' or float(value) not in cached_values:
                self.currentValueLabels[index].setText(
                    "Current value = " + str(cached_values[index])
                )
                self.currentValueLabels[index].setVisible(True)
            else:
                self.currentValueLabels[index].setVisible(False)

    def _disable_current_value_labels(self):
        for label in self.currentValueLabels:
            label.setVisible(False)

    def _set_cached_values_to_ui(self):
        _cached_values = self._get_cached_values_of_instrument_settings()
        for index, box in enumerate(self.editable_settings):
            box.setText(f'{_cached_values[index]}')

        if not self._verify_instrument_settings():
            QMessageBox.warning('Error',
                                'Current values of the instrument settings are '
                                'different than the values in the cache. Try '
                                'to reconnect to the server.')
        # Setting cached values will trigger `textChanged`. However, we do not
        # want to re-apply already cached values.
        self.instSetApply.setEnabled(False)

    def _set_ui_values_to_cache(self):
        _key_values = self._get_current_values_of_instrument_settings()
        _commands = [
            f'session.getDevice("{DEVICES[0]}")'
            f'._set_parameter("{param}", "{val}")'
            for param, val in zip(INST_SET_KEYS, _key_values)
        ]
        for cmd in _commands:
            self.client.eval(cmd)

        if not self._verify_instrument_settings():
            QMessageBox.warning(self, 'Error', 'Applied changes in instrument '
                                               'settings have not been cached.')

    def _get_cached_values_of_instrument_settings(self):
        _cached_param_values = [
            self.client.getDeviceParam(DEVICES[0], param)
            for param in INST_SET_KEYS
        ]
        return _cached_param_values

    def _get_current_values_of_instrument_settings(self):
        _box_values = [
            box.text() for box in self.editable_settings
        ]
        return _box_values

    def _is_empty(self):
        for box in self.editable_settings:
            if not box.text():
                QMessageBox.warning(self, 'Error',
                                    'A property cannot be empty.')
                box.setFocus()
                return True
        return False

    def _verify_instrument_settings(self):
        _settings_at_ui = set(
            float(x) for x in self._get_current_values_of_instrument_settings()
        )
        _settings_at_cache = set(
            self._get_cached_values_of_instrument_settings()
        )
        return _settings_at_ui == _settings_at_cache

    def _activate_environment_settings(self):
        # Enable sample environments
        self.settings = self._map_settings_to_ui()
        self.descriptionGroupBox.setVisible(True)
        self.settingsGroupBox.setVisible(True)

    def _map_settings_to_ui(self):
        _mappings = {
            'Thermostated Cell Holder': ThermoCellHolderSettings,
        }
        _ui = _mappings[self.envComboBox.currentText()](
            self.parent, self.client, self.options, self.settingsFrame
        )
        return _ui

    @pyqtSlot()
    def on_instSetApply_clicked(self):
        if self._is_empty():
            return
        self._set_ui_values_to_cache()
        self.instSetApply.setEnabled(False)
        self._disable_current_value_labels()
