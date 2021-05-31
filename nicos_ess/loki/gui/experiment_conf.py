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
import itertools

from nicos.clients.gui.utils import loadUi
from nicos.guisupport.qt import QLineEdit, QMessageBox, Qt, pyqtSlot
from nicos.utils import findResource

from nicos_ess.loki.gui.loki_panel import LokiPanelBase
from nicos_ess.utilities.validators import DoubleValidator

DEVICES = ('InstrumentSettings',)
INST_SET_KEYS = ('x', 'y', 'width', 'height', 'offset')


class LokiExperimentPanel(LokiPanelBase):
    panelName = 'LoKI Instrument Setup'

    def __init__(self, parent, client, options):
        LokiPanelBase.__init__(self, parent, client, options)
        loadUi(self, findResource('nicos_ess/loki/gui/ui_files/exp_config.ui'))

        self.holder_info = options.get('holder_info', [])
        self.instrument = options.get('instrument', 'loki')
        self.initialise_connection_status_listeners()
        self.initialise_markups()

        self.envComboBox.addItems(['Sample Changer A', 'Sample Changer B'])
        # Start with a "no item", ie, empty selection.
        self.envComboBox.setCurrentIndex(-1)

        # Hide read-only properties and hide and disable reference cell
        # positions until a sample environment is chosen by the user.
        self.propertiesGroupBox.setVisible(False)

        # Hide and disable cell position properties which shall be only
        # available for sample environments that holds them.
        self.refPosGroupBox.setVisible(False)

        self.refCellSpinBox.valueChanged.connect(
            self._set_sample_changer_ref_cell
        )

        self.envComboBox.activated.connect(self._activate_environment_settings)

        # Listen to changes in Aperture and Detector Offset values
        self.listen_instrument_settings()

        # Listen to changes in environments
        self.refPosXBox.textChanged.connect(self._set_ref_pos_x)
        self.refPosYBox.textChanged.connect(self._set_ref_pos_y)

        # Disable apply buttons in both settings until an action taken by the
        # user.
        self.sampleSetApply.setEnabled(False)
        self.instSetApply.setEnabled(False)

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
        for box in self._get_editable_settings():
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
        for box in self._get_editable_settings():
            box.setValidator(validator)

    def listen_instrument_settings(self):
        for box in self._get_editable_settings():
            box.textChanged.connect(lambda: self.instSetApply.setEnabled(True))

    def _set_cached_values_to_ui(self):
        _cached_values = self._get_cached_values_of_instrument_settings()
        for index, box in enumerate(self._get_editable_settings()):
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
            box.text() for box in self._get_editable_settings()
        ]
        return _box_values

    def _get_editable_settings(self):
        _editable_settings = itertools.chain(
                # QT returns the boxes in reverse order for some reason.
                reversed(self.aptGroupBox.findChildren(QLineEdit)),
                self.detGroupBox.findChildren(QLineEdit)
            )
        return _editable_settings

    def _activate_environment_settings(self):
        # Enable sample environments
        self.propertiesGroupBox.setVisible(True)

        self._set_cell_indices()
        self.refPosGroupBox.setVisible(True)
        self.refPosGroupBox.setEnabled(True)
        self.refCellSpinBox.setFocus()

    def _is_empty(self):
        for box in self._get_editable_settings():
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

    def _set_cell_indices(self):
        # Setting minimum and maximum values for the number of cells not only
        # ensures we have the correct numbers to choose from in the UI but also
        # prevents user errors as any integer that is not in [min, max] is not
        # allowed (or non-integer types).
        self.refCellSpinBox.setMinimum(1)

    def _set_sample_changer_ref_cell(self):
        pass

    def _set_ref_pos_x(self, value):
        pass

    def _set_ref_pos_y(self, value):
        pass

    @pyqtSlot()
    def on_instSetApply_clicked(self):
        if self._is_empty():
            return
        self._set_ui_values_to_cache()
        self.instSetApply.setEnabled(False)
