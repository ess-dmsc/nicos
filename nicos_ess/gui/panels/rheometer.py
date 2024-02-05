# *****************************************************************************
# NICOS, the Networked Instrument Control System of the MLZ
# Copyright (c) 2009-2023 by the NICOS contributors (see AUTHORS)
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
#   Jonas Petersson <jonas.petersson@ess.eu>
#
# *****************************************************************************

"""NICOS Rheometer setup panel."""
import numpy as np

from nicos.clients.gui.panels import Panel
from nicos.guisupport.qt import QFrame, QHBoxLayout, QLabel, QLineEdit, \
    QPushButton, QSplitter, Qt, QVBoxLayout, QComboBox, QGridLayout, QTableView, \
    QStandardItemModel, QStandardItem, QTimer


#########################################################
#  Some refactoring to be done, but this works for now  #
#########################################################

VISCOSITY_BASE_STRING = 'PART[($NUMB$$DTIM$),(),(),(),($MEAS_MODE$[1,$SRAT_FUNC$$STRE_FUNC$]),(),(),,(DAPT[TEMP[2,??T]],DAPT[TORQ[1,??T]],DAPT[SPEE[1,??T]],DAPT[EXCU[1,??T]],DAPT[FORC[1,??T]],DAPT[VOLT[1,??T]],DAPT[DIST[1,??T]],GSTR[STAT[1,??T]],DAPT[VELO[1,??T]],DAPT[DGAP[1,??T]],DAPT[TIMA[1,??T]],DAPT[TIMP[1,??T]],DAPT[EXCE[1,??T]],DAPT[ETRQ[1,??T]]),(GENP[0,($END_SEQ$)],SETV[0,(IFST[IN,(16)])]),($EXCU$)]'
OSCILLATION_BASE_STRING = 'PART[($NUMB$$DTIM$),(),(),(),($MEAS_MODE$[1,OSCI[$STRE_FUNC$$STRA_FUNC$$FREQ_FUNC$,SIN]]),(),(),VALF[$MEAS_MODE$[1,?&]],(VALF[$MEAS_MODE$[1,?&]],DAPT[TEMP[2,??T]],COMP[MODU[1,??F],1,PHAS],COMP[TORQ[1,??F],0,CABS],COMP[TORQ[1,??F],1,CABS],DAPT[KFAC[1,??T]],COMP[SPEE[1,??F],0,CABS],COMP[EXCU[1,??F],0,CABS],COMP[EXCU[1,??F],1,CABS],COMP[FORC[1,??F],0,REAL],DAPT[VOLT[1,??T]],DAPT[DIST[1,??T]],GSTR[STAT[1,??T]],DAPT[VELO[1,??T]],DAPT[DGAP[1,??T]],DAPT[TIMA[1,??T]],DAPT[TIMP[1,??T]],COMP[EXCE[1,??F],0,CABS],COMP[EXCE[1,??F],1,CABS],COMP[ETRQ[1,??F],0,CABS],COMP[ETRQ[1,??F],1,CABS]),(GENP[0,(IFDT[EX])],SETV[0,(IFST[IN,(16)])]),($EXCU$)]'

VISC_MODES = ['STRESS', 'RATE']
OSCI_MODES = ['STRESS', 'STRAIN']

TRANSLATE_DICT = {
    'RATE': 'SRAT',
    'STRAIN': 'STRA',
    'STRESS': 'STRE',
    # 'TORQUE': 'TORQ',
    'CONSTANT': 'CONST',
    'LINEAR': 'LIN',
    'LOGARITHMIC': 'LOG',
    'OSCILLATION': 'OSCI',
    'VISCOMETRY': 'VISC',
}


class RheometerPanel(Panel):
    panelName = 'Rheometer Setup'

    def __init__(self, parent, client, options):
        Panel.__init__(self, parent, client, options)
        self._prepared_intervals = []

        self.build_ui()
        self.setup_connections()
        self.update_ui_state()

    def build_ui(self):
        main_layout = QHBoxLayout()
        splitter = self.build_splitter()
        main_layout.addWidget(splitter)
        self.setLayout(main_layout)

    def build_splitter(self):
        edit_frame = self.build_edit_layout()
        display_frame = self.build_display_layout()

        splitter = QSplitter(Qt.Horizontal)
        splitter.addWidget(edit_frame)
        splitter.addWidget(display_frame)
        splitter.setStretchFactor(0, 0)
        splitter.setStretchFactor(1, 1)

        return splitter

    def build_edit_layout(self):
        layout = QVBoxLayout()
        frame = QFrame()

        # Mode selection
        self.mode_combo = QComboBox()
        self.mode_combo.addItems(['VISCOMETRY', 'OSCILLATION'])
        layout.addWidget(QLabel('Mode:'))
        layout.addWidget(self.mode_combo)

        # Measure Mode selection
        self.measure_mode_combo = QComboBox()
        self.measure_mode_combo.addItems(['STRESS', 'RATE', 'STRAIN'])
        layout.addWidget(QLabel('Measure Mode:'))
        layout.addWidget(self.measure_mode_combo)

        # Number of points
        num_points_layout = QHBoxLayout()
        self.num_points_le = QLineEdit()
        num_points_layout.addWidget(QLabel('Number of measurement points:'))
        num_points_layout.addWidget(self.num_points_le)
        layout.addLayout(num_points_layout)

        # duration function
        duration_layout = QGridLayout()
        self.duration_label = QLabel('Duration function [s]')
        self.duration_combo = QComboBox()
        self.duration_combo.addItems(['CONSTANT', 'LINEAR', 'LOGARITHMIC'])
        self.duration_initial_le = QLineEdit()
        self.duration_final_le = QLineEdit()
        duration_layout.addWidget(self.duration_label, 0, 0)
        duration_layout.addWidget(self.duration_combo, 1, 0)
        duration_layout.addWidget(QLabel('Initial'), 0, 1)
        duration_layout.addWidget(self.duration_initial_le, 1, 1)
        duration_layout.addWidget(QLabel('Final'), 0, 2)
        duration_layout.addWidget(self.duration_final_le, 1, 2)
        layout.addLayout(duration_layout)

        # stress function
        stress_layout = QGridLayout()
        self.stress_label = QLabel('Stress function [Pa]')
        self.stress_combo = QComboBox()
        self.stress_combo.addItems(['CONSTANT', 'LINEAR', 'LOGARITHMIC'])
        self.stress_initial_le = QLineEdit()
        self.stress_final_le = QLineEdit()
        stress_layout.addWidget(self.stress_label, 0, 0)
        stress_layout.addWidget(self.stress_combo, 1, 0)
        stress_layout.addWidget(QLabel('Initial'), 0, 1)
        stress_layout.addWidget(self.stress_initial_le, 1, 1)
        stress_layout.addWidget(QLabel('Final'), 0, 2)
        stress_layout.addWidget(self.stress_final_le, 1, 2)
        layout.addLayout(stress_layout)

        # rate function
        rate_layout = QGridLayout()
        self.rate_label = QLabel('Rate function [1/s]')
        self.rate_combo = QComboBox()
        self.rate_combo.addItems(['CONSTANT', 'LINEAR', 'LOGARITHMIC'])
        self.rate_initial_le = QLineEdit()
        self.rate_final_le = QLineEdit()
        rate_layout.addWidget(self.rate_label, 0, 0)
        rate_layout.addWidget(self.rate_combo, 1, 0)
        rate_layout.addWidget(QLabel('Initial'), 0, 1)
        rate_layout.addWidget(self.rate_initial_le, 1, 1)
        rate_layout.addWidget(QLabel('Final'), 0, 2)
        rate_layout.addWidget(self.rate_final_le, 1, 2)
        layout.addLayout(rate_layout)

        # Strain function
        strain_layout = QGridLayout()
        self.strain_label = QLabel('Strain function [%]')
        self.strain_combo = QComboBox()
        self.strain_combo.addItems(['CONSTANT', 'LINEAR', 'LOGARITHMIC'])
        self.strain_initial_le = QLineEdit()
        self.strain_final_le = QLineEdit()
        strain_layout.addWidget(self.strain_label, 0, 0)
        strain_layout.addWidget(self.strain_combo, 1, 0)
        strain_layout.addWidget(QLabel('Initial'), 0, 1)
        strain_layout.addWidget(self.strain_initial_le, 1, 1)
        strain_layout.addWidget(QLabel('Final'), 0, 2)
        strain_layout.addWidget(self.strain_final_le, 1, 2)
        layout.addLayout(strain_layout)

        # Frequency function
        frequency_layout = QGridLayout()
        self.frequency_label = QLabel('Frequency function [rad/s]')
        self.frequency_combo = QComboBox()
        self.frequency_combo.addItems(['CONSTANT', 'LINEAR', 'LOGARITHMIC'])
        self.frequency_initial_le = QLineEdit()
        self.frequency_final_le = QLineEdit()
        frequency_layout.addWidget(self.frequency_label, 0, 0)
        frequency_layout.addWidget(self.frequency_combo, 1, 0)
        frequency_layout.addWidget(QLabel('Initial'), 0, 1)
        frequency_layout.addWidget(self.frequency_initial_le, 1, 1)
        frequency_layout.addWidget(QLabel('Final'), 0, 2)
        frequency_layout.addWidget(self.frequency_final_le, 1, 2)
        layout.addLayout(frequency_layout)

        layout.addStretch()

        # Add interval button
        self.add_interval_button = QPushButton('Add interval')
        layout.addWidget(self.add_interval_button)

        # Clear intervals button
        self.clear_intervals_button = QPushButton('Clear intervals')
        layout.addWidget(self.clear_intervals_button)

        # Send intervals button
        self.send_intervals_button = QPushButton('Send intervals')
        layout.addWidget(self.send_intervals_button)

        frame.setLayout(layout)

        return frame

    def build_display_layout(self):
        layout = QVBoxLayout()
        frame = QFrame()

        self.tableView = QTableView()
        self.tableModel = QStandardItemModel()
        self.tableView.setModel(self.tableModel)

        self.tableView.setWordWrap(True)
        self.tableView.setTextElideMode(Qt.ElideNone)

        self.tableModel.setHorizontalHeaderLabels(['Interval', 'Mode', 'Measure Mode', 'Number of Points', 'Duration', 'Stress', 'Rate', 'Strain', 'Frequency'])

        layout.addWidget(self.tableView)

        frame.setLayout(layout)

        return frame

    def get_interval(self):
        interval = {}
        interval['mode'] = self.mode_combo.currentText()
        interval['measure_mode'] = self.measure_mode_combo.currentText()
        interval['num_points'] = self.num_points_le.text()

        duration_function = self.duration_combo.currentText()
        if duration_function == 'CONSTANT':
            interval['duration'] = (
                TRANSLATE_DICT[duration_function],
                self.duration_initial_le.text(),
                self.duration_initial_le.text()
            )
        else:
            # The rheometer expects the format as ((initial, second_last), final)
            if duration_function == 'LINEAR':
                points = np.linspace(
                    float(self.duration_initial_le.text()),
                    float(self.duration_final_le.text()),
                    int(self.num_points_le.text())
                )
                second_last_point = points[-2]
            elif duration_function == 'LOGARITHMIC':
                points = np.logspace(
                    np.log10(float(self.duration_initial_le.text())),
                    np.log10(float(self.duration_final_le.text())),
                    int(self.num_points_le.text())
                )
                second_last_point = points[-2]
            else:
                raise ValueError(f"Invalid duration function: {duration_function}")

            interval['duration'] = (
                TRANSLATE_DICT[duration_function],
                (self.duration_initial_le.text(), str(second_last_point)),
                self.duration_final_le.text()
            )

        interval['funcs'] = {}

        if self.rate_combo.isEnabled():
            interval['funcs']['srat'] = (
                TRANSLATE_DICT[self.rate_combo.currentText()],
                self.rate_initial_le.text(),
                self.rate_final_le.text()
            )

        if self.strain_combo.isEnabled():
            interval['funcs']['stra'] = (
                TRANSLATE_DICT[self.strain_combo.currentText()],
                self._convert_to_percent(self.strain_initial_le.text()),
                self._convert_to_percent(self.strain_final_le.text())
            )

        if self.stress_combo.isEnabled():
            interval['funcs']['stre'] = (
                TRANSLATE_DICT[self.stress_combo.currentText()],
                self.stress_initial_le.text(),
                self.stress_final_le.text()
            )

        if self.frequency_combo.isEnabled():
            interval['funcs']['freq'] = (
                TRANSLATE_DICT[self.frequency_combo.currentText()],
                self._convert_to_rad_per_sec(self.frequency_initial_le.text()),
                self._convert_to_rad_per_sec(self.frequency_final_le.text())
            )

        if not self.valid_function(interval['funcs']):
            return {}

        return interval

    def _convert_to_rad_per_sec(self, value):
        if value == '':
            return ''
        return str(float(value) / (2 * np.pi))

    def _convert_to_percent(self, value):
        if value == '':
            return ''
        return str(float(value) / 100.)

    def valid_function(self, function):
        for key, value in function.items():
            function_type = value[0]
            ignore_final = True if function_type == 'CONST' else False
            for i, val in enumerate(value):
                if ignore_final and i == 2:
                    continue
                if val == '':
                    return False
        return True

    def add_interval_to_table(self):
        # Create QStandardItems from the interval data

        interval = self.get_interval()

        if not interval:
            return

        items = []

        current_num_intervals = self.tableModel.rowCount()
        items.append(QStandardItem(str(current_num_intervals + 1)))

        for key in ['mode', 'measure_mode', 'num_points']:
            content = str(interval.get(key, ''))
            item = QStandardItem(content)
            items.append(item)

        content = self._display_format_duration(interval['duration'])
        item = QStandardItem(content)
        items.append(item)

        for func in ['stre', 'srat', 'stra', 'freq']:
            if func not in interval['funcs']:
                items.append(QStandardItem(''))
                continue
            content = self._display_format_function(interval['funcs'][func])
            item = QStandardItem(content)
            items.append(item)

        # self.tableView.resizeRowsToContents()
        QTimer.singleShot(0, self.tableView.resizeRowsToContents)
        QTimer.singleShot(0, self.resize_columns)

        self.tableModel.appendRow(items)

        self._prepared_intervals.append(interval)

    def _display_format_function(self, function):
        if function[0] == 'CONST':
            return f'Function: {function[0]}({function[1]})'
        return f'Function: {function[0]}({function[1]}, {function[2]}))'

    def _display_format_duration(self, duration):
        if duration[0] == 'CONST':
            return f'Function: {duration[0]}({duration[1]})'
        return f'Function: {duration[0]}({duration[1][0]}, {duration[2]}))'

    def send_intervals(self):
        if not self._prepared_intervals:
            return
        command_string = self._build_command(self._prepared_intervals)
        print('\n')
        print('\n')
        print(command_string)
        print('\n')
        print('\n')

        self.client.tell('exec', f"rheo_control.set_command_string('{command_string}')")

    def resize_columns(self):
        table_width = self.tableView.width()
        num_columns = self.tableModel.columnCount()
        current_width = table_width / num_columns

        self.tableView.resizeColumnsToContents()

        function_columns = [4, 5, 6, 7, 8]
        for col in function_columns:
            self.tableView.setColumnWidth(col, int(current_width * 1.2))

    def clear_table(self):
        self.tableModel.clear()
        self._prepared_intervals = []
        self.tableModel.setHorizontalHeaderLabels(['Interval', 'Mode', 'Measure Mode', 'Number of Points', 'Duration', 'Stress', 'Rate', 'Strain', 'Frequency'])

    def setup_connections(self):
        self.mode_combo.currentIndexChanged.connect(self.update_ui_state)
        self.measure_mode_combo.currentIndexChanged.connect(self.update_ui_state)
        self.duration_combo.currentIndexChanged.connect(self.update_ui_state)
        self.stress_combo.currentIndexChanged.connect(self.update_ui_state)
        self.rate_combo.currentIndexChanged.connect(self.update_ui_state)
        self.strain_combo.currentIndexChanged.connect(self.update_ui_state)
        self.frequency_combo.currentIndexChanged.connect(self.update_ui_state)
        self.add_interval_button.clicked.connect(self.add_interval_to_table)
        self.clear_intervals_button.clicked.connect(self.clear_table)
        self.send_intervals_button.clicked.connect(self.send_intervals)

    def update_ui_state(self):
        # Get current selections
        mode = self.mode_combo.currentText()
        measure_mode = self.measure_mode_combo.currentText()

        illegal_state = False

        self.disable_all()

        # Logic for VISC mode
        if mode == 'VISCOMETRY':
            # if measure_mode == 'stress':
            #     self.measure_mode_combo.setCurrentIndex(0)
            if measure_mode == 'RATE':
                self.set_enabled_state(True, [self.rate_combo, self.rate_initial_le, self.rate_final_le])
            elif measure_mode == 'STRESS':
                self.set_enabled_state(True, [self.stress_combo, self.stress_initial_le, self.stress_final_le])

            self.measure_mode_combo.blockSignals(True)
            self.measure_mode_combo.clear()
            self.measure_mode_combo.addItems(VISC_MODES)
            if measure_mode not in VISC_MODES:
                illegal_state = True
                self.measure_mode_combo.setCurrentIndex(0)
                measure_mode = self.measure_mode_combo.currentText()
            self.measure_mode_combo.setCurrentIndex(VISC_MODES.index(measure_mode))
            self.measure_mode_combo.blockSignals(False)

        # Logic for OSCI mode
        elif mode == 'OSCILLATION':
            if measure_mode == 'STRESS':
                self.set_enabled_state(True, [self.stress_combo, self.stress_initial_le, self.stress_final_le,
                                              self.frequency_combo, self.frequency_initial_le, self.frequency_final_le])
            else:
                self.set_enabled_state(True, [self.strain_combo, self.strain_initial_le, self.strain_final_le,
                                              self.frequency_combo, self.frequency_initial_le, self.frequency_final_le])

            self.measure_mode_combo.blockSignals(True)
            self.measure_mode_combo.clear()
            self.measure_mode_combo.addItems(OSCI_MODES)
            if measure_mode not in OSCI_MODES:
                illegal_state = True
                self.measure_mode_combo.setCurrentIndex(1)
                measure_mode = self.measure_mode_combo.currentText()
            self.measure_mode_combo.setCurrentIndex(OSCI_MODES.index(measure_mode))
            self.measure_mode_combo.blockSignals(False)

        for (func, final_le) in [('duration', self.duration_final_le),
                                  ('stress', self.stress_final_le),
                                  ('rate', self.rate_final_le),
                                  ('strain', self.strain_final_le),
                                  ('frequency', self.frequency_final_le)]:
            if getattr(self, f'{func}_combo').currentText() == 'CONSTANT':
                self.set_enabled_state(False, [final_le])
            elif not getattr(self, f'{func}_combo').isEnabled():
                self.set_enabled_state(False, [final_le])
            else:
                self.set_enabled_state(True, [final_le])

        #  If we swapped state to an illegal state, we need to update the UI again to reflect the new state
        #  Because we block some signals during the update. This is a bit of a hack, but it works for now.
        if illegal_state:
            self.update_ui_state()

    def set_enabled_state(self, enabled, widgets):
        for widget in widgets:
            widget.setEnabled(enabled)
            if not enabled:
                widget.setStyleSheet("color: gray; background-color: lightgray;")
            else:
                widget.setStyleSheet("")

    def disable_all(self):
        self.set_enabled_state(False, [self.rate_combo, self.rate_initial_le, self.rate_final_le,
                                       self.strain_combo, self.strain_initial_le, self.strain_final_le,
                                       self.frequency_combo, self.frequency_initial_le, self.frequency_final_le,
                                       self.stress_combo, self.stress_initial_le, self.stress_final_le])

    def _build_command(self, intervals):
        if not intervals:
            raise ValueError("No intervals provided for the measurement.")

        parts_string = ','.join([self._construct_interval_command(interval, index == 0)
                                 for index, interval in enumerate(intervals)])

        return f':PROG["Test",TEST[({parts_string})],EXIT[()],CANC[()]]'

    def _construct_interval_command(self, interval, is_first_interval):
        mode = interval.get('mode', None)
        if mode == 'VISCOMETRY':
            return self._construct_viscosity_interval(interval, is_first_interval)
        elif mode == 'OSCILLATION':
            return self._construct_oscillation_interval(interval, is_first_interval)
        else:
            raise ValueError(f"Invalid mode: {mode}")

    def _construct_viscosity_interval(self, interval, is_first_interval):
        meas_mode = interval.get('measure_mode', None)
        if meas_mode is None:
            raise ValueError("No measure mode provided for the interval.")

        required_params = ['num_points', 'measure_mode', 'duration', 'funcs', 'end_seq']

        num_points, measure_mode, duration, funcs, end_seq = self._get_required_params(interval, required_params)
        measure_mode = TRANSLATE_DICT[measure_mode]
        duration_str = self._format_duration(duration)
        func_strings = {}
        for func in funcs:
            func_strings[func] = self._format_func(funcs[func])

        excu_str = 'EXCU[1,!?]' if is_first_interval else ''

        temp_string = VISCOSITY_BASE_STRING.replace('$NUMB$', f'NUMB[{num_points},LAST]')\
                                    .replace('$DTIM$', duration_str)\
                                    .replace('$MEAS_MODE$', measure_mode)\
                                    .replace('$END_SEQ$', end_seq)\
                                    .replace('$EXCU$', excu_str)

        for i, (func_type, func_string) in enumerate(func_strings.items()):
            print(f"iteration {i} with func type {func_type} and func string {func_string}")
            if i != 0:
                func_string = ',' + func_string
            temp_string = temp_string.replace(f'${func_type.upper()}_FUNC$', func_string)

        return self._remove_all_remaining_placeholders(temp_string)

    def _construct_oscillation_interval(self, interval, is_first_interval):
        meas_mode = interval.get('measure_mode', None)
        if meas_mode is None:
            raise ValueError("No measure mode provided for the interval.")

        required_params = ['num_points', 'measure_mode', 'duration', 'funcs', 'end_seq']

        num_points, measure_mode, duration, funcs, end_seq = self._get_required_params(interval, required_params)
        measure_mode = TRANSLATE_DICT[measure_mode]
        duration_str = self._format_duration(duration)
        func_strings = {}
        for func in funcs:
            func_strings[func] = self._format_func(funcs[func])

        excu_str = 'EXCU[1,!?]' if is_first_interval else ''

        temp_string = OSCILLATION_BASE_STRING.replace('$NUMB$', f'NUMB[{num_points},LAST]')\
                                      .replace('$DTIM$', duration_str)\
                                      .replace('$MEAS_MODE$', measure_mode)\
                                      .replace('$END_SEQ$', end_seq)\
                                      .replace('$EXCU$', excu_str)

        for i, (func_type, func_string) in enumerate(func_strings.items()):
            if i != 0:
                func_string = ',' + func_string
            temp_string = temp_string.replace(f'${func_type.upper()}_FUNC$', func_string)

        return self._remove_all_remaining_placeholders(temp_string)

    def _remove_all_remaining_placeholders(self, string):
        return string.replace('$NUMB$', '')\
                     .replace('$DTIM$', '')\
                     .replace('$MEAS_MODE$', '')\
                     .replace('$END_SEQ$', '')\
                     .replace('$EXCU$', '') \
                     .replace('$SRAT_FUNC$', '') \
                     .replace('$STRA_FUNC$', '')\
                     .replace('$FREQ_FUNC$', '')\
                     .replace('$STRE_FUNC$', '')

    def _get_required_params(self, interval, keys):
        missing_params = [key for key in keys if key not in interval]
        for param in missing_params:
            if param == 'duration':
                interval[param] = (None, None, None)
            elif param == 'end_seq':
                interval[param] = 'IFDT[EX]'
            else:
                raise ValueError(f"Missing parameter: {param}")
        return [interval[key] for key in keys]

    def _format_duration(self, duration):
        if duration is None or all(v is None for v in duration[0:2]):
            return ''
        duration_type, point_info, duration_final = duration
        duration_second_last = None
        if isinstance(point_info, tuple):
            duration_initial, duration_second_last = point_info
        else:
            duration_initial = point_info
        if duration_type == 'CONST':
            return f',DTIM[{duration_initial},{duration_initial},REL]'
        elif duration_type in ['LIN', 'LOG']:
            if duration_second_last is None or duration_final is None:
                return ''
            return f',DTIM[FUNC[{duration_type},({duration_initial},{duration_second_last})],{duration_final},REL]'
        else:
            raise ValueError(f"Invalid duration type: {duration_type}")

    def _format_func(self, func):
        if func is None or all(v is None for v in func[0:2]):
            return ''
        func_type, func_initial, func_final = func
        if func_type == 'CONST':
            return f'{func_initial}'

        if func_final is None:
            return ''

        temp_string = f'FUNC[{func_type},({func_initial},{func_final})]'

        return temp_string