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

from nicos.clients.gui.panels import Panel
from nicos.guisupport.qt import QFrame, QGroupBox, QHBoxLayout, QLabel, \
    QLineEdit, QPushButton, QScrollArea, QSize, QSizePolicy, QSplitter, Qt, \
    QTabWidget, QVBoxLayout, QWidget, pyqtProperty, pyqtSignal, pyqtSlot, \
    QCheckBox, QComboBox, QGridLayout, QTableView, QStandardItemModel, \
    QStandardItem, QTimer


VISCOSITY_BASE_STRING = 'PART[($NUMB$$DTIM$),(),(),(),($MEAS_MODE$[1,$SPEED_FUNC$]),(),(),,(DAPT[TEMP[2,??T]],DAPT[TORQ[1,??T]],DAPT[SPEE[1,??T]],DAPT[EXCU[1,??T]],DAPT[FORC[1,??T]],DAPT[VOLT[1,??T]],DAPT[DIST[1,??T]],GSTR[STAT[1,??T]],DAPT[VELO[1,??T]],DAPT[DGAP[1,??T]],DAPT[TIMA[1,??T]],DAPT[TIMP[1,??T]],DAPT[EXCE[1,??T]],DAPT[ETRQ[1,??T]]),(GENP[0,($END_SEQ$)],SETV[0,(IFST[IN,(16)])]),($EXCU$)]'
OSCILLATION_BASE_STRING = 'PART[($NUMB$$DTIM$),(),(),(),($MEAS_MODE$[1,OSCI[$AMP_FUNC$$FREQ_FUNC$$TORQ_FUNC$,SIN]]),(),(),VALF[$MEAS_MODE$[1,?&]],(VALF[$MEAS_MODE$[1,?&]],DAPT[TEMP[2,??T]],COMP[MODU[1,??F],1,PHAS],COMP[TORQ[1,??F],0,CABS],COMP[TORQ[1,??F],1,CABS],DAPT[KFAC[1,??T]],COMP[SPEE[1,??F],0,CABS],COMP[EXCU[1,??F],0,CABS],COMP[EXCU[1,??F],1,CABS],COMP[FORC[1,??F],0,REAL],DAPT[VOLT[1,??T]],DAPT[DIST[1,??T]],GSTR[STAT[1,??T]],DAPT[VELO[1,??T]],DAPT[DGAP[1,??T]],DAPT[TIMA[1,??T]],DAPT[TIMP[1,??T]],COMP[EXCE[1,??F],0,CABS],COMP[EXCE[1,??F],1,CABS],COMP[ETRQ[1,??F],0,CABS],COMP[ETRQ[1,??F],1,CABS]),(GENP[0,(IFDT[EX])],SETV[0,(IFST[IN,(16)])]),($EXCU$)]'

VISC_MODES = ['SHEAR', 'STRAIN']
OSCI_MODES = ['SHEAR', 'STRAIN', 'TORQUE']

TRANSLATE_DICT = {
    'SHEAR': 'SRAT',
    'STRAIN': 'STRA',
    'TORQUE': 'TORQ',
    'CONSTANT': 'CONST',
    'LINEAR': 'LIN',
    'LOGARITHMIC': 'LOG'
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
        self.mode_combo.addItems(['VISC', 'OSCI'])
        layout.addWidget(QLabel('Mode:'))
        layout.addWidget(self.mode_combo)

        # Measure Mode selection
        self.measure_mode_combo = QComboBox()
        self.measure_mode_combo.addItems(['SHEAR', 'STRAIN', 'TORQUE'])
        layout.addWidget(QLabel('Measure Mode:'))
        layout.addWidget(self.measure_mode_combo)

        # Number of points
        num_points_layout = QHBoxLayout()
        self.num_points_le = QLineEdit()
        num_points_layout.addWidget(QLabel('Number of measurement points:'))
        num_points_layout.addWidget(self.num_points_le)
        layout.addLayout(num_points_layout)

        # Delay function
        delay_layout = QGridLayout()
        self.delay_label = QLabel('Delay function:')
        self.delay_combo = QComboBox()
        self.delay_combo.addItems(['CONSTANT', 'LINEAR', 'LOGARITHMIC'])
        self.delay_initial_le = QLineEdit()
        self.delay_final_le = QLineEdit()
        self.delay_wait_le = QLineEdit()
        delay_layout.addWidget(self.delay_label, 0, 0)
        delay_layout.addWidget(self.delay_combo, 1, 0)
        delay_layout.addWidget(QLabel('initial:'), 0, 1)
        delay_layout.addWidget(self.delay_initial_le, 1, 1)
        delay_layout.addWidget(QLabel('final:'), 0, 2)
        delay_layout.addWidget(self.delay_final_le, 1, 2)
        delay_layout.addWidget(QLabel('Wait:'), 0, 3)
        delay_layout.addWidget(self.delay_wait_le, 1, 3)
        layout.addLayout(delay_layout)

        # Speed function
        speed_layout = QGridLayout()
        self.speed_label = QLabel('Speed function:')
        self.speed_combo = QComboBox()
        self.speed_combo.addItems(['CONSTANT', 'LINEAR', 'LOGARITHMIC'])
        self.speed_initial_le = QLineEdit()
        self.speed_final_le = QLineEdit()
        speed_layout.addWidget(self.speed_label, 0, 0)
        speed_layout.addWidget(self.speed_combo, 1, 0)
        speed_layout.addWidget(QLabel('initial:'), 0, 1)
        speed_layout.addWidget(self.speed_initial_le, 1, 1)
        speed_layout.addWidget(QLabel('final:'), 0, 2)
        speed_layout.addWidget(self.speed_final_le, 1, 2)
        layout.addLayout(speed_layout)

        # Amplitude function
        amplitude_layout = QGridLayout()
        self.amplitude_label = QLabel('Amplitude function:')
        self.amplitude_combo = QComboBox()
        self.amplitude_combo.addItems(['CONSTANT', 'LINEAR', 'LOGARITHMIC'])
        self.amplitude_initial_le = QLineEdit()
        self.amplitude_final_le = QLineEdit()
        amplitude_layout.addWidget(self.amplitude_label, 0, 0)
        amplitude_layout.addWidget(self.amplitude_combo, 1, 0)
        amplitude_layout.addWidget(QLabel('initial:'), 0, 1)
        amplitude_layout.addWidget(self.amplitude_initial_le, 1, 1)
        amplitude_layout.addWidget(QLabel('final:'), 0, 2)
        amplitude_layout.addWidget(self.amplitude_final_le, 1, 2)
        layout.addLayout(amplitude_layout)

        # Frequency function
        frequency_layout = QGridLayout()
        self.frequency_label = QLabel('Frequency function:')
        self.frequency_combo = QComboBox()
        self.frequency_combo.addItems(['CONSTANT', 'LINEAR', 'LOGARITHMIC'])
        self.frequency_initial_le = QLineEdit()
        self.frequency_final_le = QLineEdit()
        frequency_layout.addWidget(self.frequency_label, 0, 0)
        frequency_layout.addWidget(self.frequency_combo, 1, 0)
        frequency_layout.addWidget(QLabel('initial:'), 0, 1)
        frequency_layout.addWidget(self.frequency_initial_le, 1, 1)
        frequency_layout.addWidget(QLabel('final:'), 0, 2)
        frequency_layout.addWidget(self.frequency_final_le, 1, 2)
        layout.addLayout(frequency_layout)

        # Torque function
        torque_layout = QGridLayout()
        self.torque_label = QLabel('Torque function:')
        self.torque_combo = QComboBox()
        self.torque_combo.addItems(['CONSTANT', 'LINEAR', 'LOGARITHMIC'])
        self.torque_initial_le = QLineEdit()
        self.torque_final_le = QLineEdit()
        torque_layout.addWidget(self.torque_label, 0, 0)
        torque_layout.addWidget(self.torque_combo, 1, 0)
        torque_layout.addWidget(QLabel('initial:'), 0, 1)
        torque_layout.addWidget(self.torque_initial_le, 1, 1)
        torque_layout.addWidget(QLabel('final:'), 0, 2)
        torque_layout.addWidget(self.torque_final_le, 1, 2)
        layout.addLayout(torque_layout)

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

        self.tableModel.setHorizontalHeaderLabels(['Interval', 'Mode', 'Measure Mode', 'Number of Points', 'Delay', 'Speed', 'Amplitude', 'Frequency', 'Torque'])

        layout.addWidget(self.tableView)

        frame.setLayout(layout)

        return frame

    def get_interval(self):
        interval = {}
        interval['mode'] = self.mode_combo.currentText()
        interval['measure_mode'] = self.measure_mode_combo.currentText()
        interval['num_points'] = self.num_points_le.text()

        delay_function = self.delay_combo.currentText()
        if delay_function == 'CONSTANT':
            interval['delay'] = (
                TRANSLATE_DICT[delay_function],
                self.delay_initial_le.text(),
                self.delay_wait_le.text()
            )
        else:
            interval['delay'] = (
                TRANSLATE_DICT[delay_function],
                (self.delay_initial_le.text(), self.delay_final_le.text()),
                self.delay_wait_le.text()
            )

        interval['funcs'] = {}

        if self.speed_combo.isEnabled():
            interval['funcs']['speed'] = (
                TRANSLATE_DICT[self.speed_combo.currentText()],
                self.speed_initial_le.text(),
                self.speed_final_le.text()
            )

        if self.amplitude_combo.isEnabled():
            interval['funcs']['amp'] = (
                TRANSLATE_DICT[self.amplitude_combo.currentText()],
                self.amplitude_initial_le.text(),
                self.amplitude_final_le.text()
            )

        if self.frequency_combo.isEnabled():
            interval['funcs']['freq'] = (
                TRANSLATE_DICT[self.frequency_combo.currentText()],
                self.frequency_initial_le.text(),
                self.frequency_final_le.text()
            )

        if self.torque_combo.isEnabled():
            interval['funcs']['torq'] = (
                TRANSLATE_DICT[self.torque_combo.currentText()],
                self.torque_initial_le.text(),
                self.torque_final_le.text()
            )

        if not self.valid_function(interval['funcs']):
            return {}

        return interval

    def valid_function(self, function):
        for key, value in function.items():
            for val in value:
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

        content = self._display_format_delay(interval['delay'])
        item = QStandardItem(content)
        items.append(item)

        for func in ['speed', 'amp', 'freq', 'torq']:
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
        return f'Function: {function[0]}({function[1]}, {function[2]}))'

    def _display_format_delay(self, delay):
        if delay[0] == 'CONST':
            return f'Function: {delay[0]}({delay[1]}), wait: {delay[2]})'
        return f'Function: {delay[0]}({delay[1][0]}, {delay[1][1]}), wait: {delay[2]})'

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
        self.tableModel.setHorizontalHeaderLabels(['Interval', 'Mode', 'Measure Mode', 'Number of Points', 'Delay', 'Speed', 'Amplitude', 'Frequency', 'Torque'])

    def setup_connections(self):
        self.mode_combo.currentIndexChanged.connect(self.update_ui_state)
        self.measure_mode_combo.currentIndexChanged.connect(self.update_ui_state)
        self.add_interval_button.clicked.connect(self.add_interval_to_table)
        self.clear_intervals_button.clicked.connect(self.clear_table)
        self.send_intervals_button.clicked.connect(self.send_intervals)

    def update_ui_state(self):
        # Get current selections
        mode = self.mode_combo.currentText()
        measure_mode = self.measure_mode_combo.currentText()

        self.disable_all()

        # Logic for VISC mode
        if mode == 'VISC':
            # if measure_mode == 'TORQUE':
            #     self.measure_mode_combo.setCurrentIndex(0)

            self.set_enabled_state(True, [self.speed_combo, self.speed_initial_le, self.speed_final_le])

            self.measure_mode_combo.blockSignals(True)
            self.measure_mode_combo.clear()
            self.measure_mode_combo.addItems(VISC_MODES)
            if measure_mode not in VISC_MODES:
                self.measure_mode_combo.setCurrentIndex(0)
                measure_mode = self.measure_mode_combo.currentText()
            self.measure_mode_combo.setCurrentIndex(VISC_MODES.index(measure_mode))
            self.measure_mode_combo.blockSignals(False)

        # Logic for OSCI mode
        elif mode == 'OSCI':
            if measure_mode == 'TORQUE':
                self.set_enabled_state(True, [self.torque_combo, self.torque_initial_le, self.torque_final_le])
                # return
            else:
                self.set_enabled_state(True, [self.amplitude_combo, self.amplitude_initial_le, self.amplitude_final_le,
                                              self.frequency_combo, self.frequency_initial_le, self.frequency_final_le])

            self.measure_mode_combo.blockSignals(True)
            self.measure_mode_combo.clear()
            self.measure_mode_combo.addItems(OSCI_MODES)
            self.measure_mode_combo.setCurrentIndex(OSCI_MODES.index(measure_mode))
            self.measure_mode_combo.blockSignals(False)

    def set_enabled_state(self, enabled, widgets):
        for widget in widgets:
            widget.setEnabled(enabled)
            if not enabled:
                widget.setStyleSheet("color: gray; background-color: lightgray;")
            else:
                widget.setStyleSheet("")

    def disable_all(self):
        self.set_enabled_state(False, [self.speed_combo, self.speed_initial_le, self.speed_final_le,
                                       self.amplitude_combo, self.amplitude_initial_le, self.amplitude_final_le,
                                       self.frequency_combo, self.frequency_initial_le, self.frequency_final_le,
                                       self.torque_combo, self.torque_initial_le, self.torque_final_le])

    def _build_command(self, intervals):
        if not intervals:
            raise ValueError("No intervals provided for the measurement.")

        parts_string = ','.join([self._construct_interval_command(interval, index == 0)
                                 for index, interval in enumerate(intervals)])

        return f':PROG["Test",TEST[({parts_string})],EXIT[()],CANC[()]]'

    def _construct_interval_command(self, interval, is_first_interval):
        mode = interval.get('mode', None)
        if mode == 'VISC':
            return self._construct_viscosity_interval(interval, is_first_interval)
        elif mode == 'OSCI':
            return self._construct_oscillation_interval(interval, is_first_interval)
        else:
            raise ValueError(f"Invalid mode: {mode}")

    def _construct_viscosity_interval(self, interval, is_first_interval):
        meas_mode = interval.get('measure_mode', None)
        if meas_mode is None:
            raise ValueError("No measure mode provided for the interval.")

        required_params = ['num_points', 'measure_mode', 'delay', 'funcs', 'end_seq']

        num_points, measure_mode, delay, funcs, end_seq = self._get_required_params(interval, required_params)
        delay_str = self._format_delay(delay)
        func_strings = {}
        for func in funcs:
            func_strings[func] = self._format_func(funcs[func])

        excu_str = 'EXCU[1,!?]' if is_first_interval else ''

        temp_string = VISCOSITY_BASE_STRING.replace('$NUMB$', f'NUMB[{num_points},LAST]')\
                                    .replace('$DTIM$', delay_str)\
                                    .replace('$MEAS_MODE$', meas_mode)\
                                    .replace('$END_SEQ$', end_seq)\
                                    .replace('$EXCU$', excu_str)

        for func_type, func_string in func_strings.items():
            temp_string = temp_string.replace(f'${func_type.upper()}_FUNC$', func_string)

        return temp_string

    def _construct_oscillation_interval(self, interval, is_first_interval):
        meas_mode = interval.get('measure_mode', None)
        if meas_mode is None:
            raise ValueError("No measure mode provided for the interval.")

        required_params = ['num_points', 'measure_mode', 'delay', 'funcs', 'end_seq']

        num_points, measure_mode, delay, funcs, end_seq = self._get_required_params(interval, required_params)
        delay_str = self._format_delay(delay)
        wait_time = delay[2] if delay is not None and measure_mode == 'TORQ' else None
        func_strings = {}
        for func in funcs:
            func_strings[func] = self._format_func(funcs[func], wait_time)

        excu_str = 'EXCU[1,!?]' if is_first_interval else ''

        temp_string = OSCILLATION_BASE_STRING.replace('$NUMB$', f'NUMB[{num_points},LAST]')\
                                      .replace('$DTIM$', delay_str)\
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
                     .replace('$EXCU$', '')\
                     .replace('$AMP_FUNC$', '')\
                     .replace('$FREQ_FUNC$', '')\
                     .replace('$TORQ_FUNC$', '')

    def _get_required_params(self, interval, keys):
        missing_params = [key for key in keys if key not in interval]
        for param in missing_params:
            if param == 'delay':
                interval[param] = (None, None, None)
            elif param == 'end_seq':
                interval[param] = 'IFDT[EX]'
            else:
                raise ValueError(f"Missing parameter: {param}")
        return [interval[key] for key in keys]

    def _format_delay(self, delay):
        if delay is None or all(v is None for v in delay):
            return ''
        delay_type, time_info, wait_time = delay
        if isinstance(time_info, tuple):
            delay_initial, delay_final = time_info
        else:
            delay_initial = delay_final = time_info
        if delay_type == 'CONST':
            return f',DTIM[{delay_initial},{wait_time},REL]'
        elif delay_type in ['LIN', 'LOG']:
            return f',DTIM[FUNC[{delay_type},({delay_initial},{delay_final})],{wait_time},REL]'
        else:
            raise ValueError(f"Invalid delay type: {delay_type}")

    def _format_func(self, func, wait_time=None):
        if func is None or all(v is None for v in func):
            return ''
        func_type, func_initial, func_final = func
        if func_type == 'CONST':
            return f'{func_initial}'

        temp_string = f'FUNC[{func_type},({func_initial},{func_final})]'
        if wait_time is not None:
            temp_string += f',{wait_time}'

        return temp_string