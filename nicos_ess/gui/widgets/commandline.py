import re

from nicos.clients.gui.utils import ScriptExecQuestion
from nicos.guisupport.colors import colors
from nicos.guisupport.qt import (
    QApplication,
    QColor,
    QCompleter,
    QEvent,
    QKeyEvent,
    QLineEdit,
    QMessageBox,
    QRegularExpression,
    QRegularExpressionValidator,
    QStringListModel,
    Qt,
    pyqtSignal,
)
from nicos.guisupport.utils import setBackgroundColor, setForegroundColor

from nicos_ess.gui.utils import State, StyleSelector, refresh_widget

wordsplit_re = re.compile(r"[ \t\n\"\\\'`@$><=;|&{(\[]")


class CommandLineEdit(QLineEdit, StyleSelector):
    """
    A NICOS command input line with history.
    """

    escapePressed = pyqtSignal()
    execRequested = pyqtSignal(str, str)

    scrollingKeys = [
        Qt.Key.Key_Up,
        Qt.Key.Key_Down,
        Qt.Key.Key_PageUp,
        Qt.Key.Key_PageDown,
    ]

    def __init__(self, parent, history=None):
        QLineEdit.__init__(self, parent)
        self.run_color = colors.cmd_running
        self.idle_color = colors.base
        self.active_fgcolor = colors.text
        self.inactive_fgcolor = colors.cmd_inactive
        self.error_fgcolor = QColor("#ff0000")
        self.history = history or []
        self.scrollWidget = None
        self.completion_callback = lambda text: []
        self._start_text = ""
        self._current = -1
        self._completer = QCompleter([], self)
        self.setCompleter(self._completer)
        self.textChanged.connect(self.on_textChanged)
        self.returnPressed.connect(self.on_returnPressed)
        self.setValidator(
            QRegularExpressionValidator(QRegularExpression(r"^\S.*"), self)
        )
        self.current_status = None
        self.error_status = None

    def event(self, event):
        # need to reimplement the general event handler to enable catching Tab
        if event.type() == QEvent.Type.KeyPress and event.key() == Qt.Key.Key_Tab:
            fullstring = self.text()
            lastword = wordsplit_re.split(fullstring)[-1]
            # pylint: disable=too-many-function-args
            matches = self.completion_callback(fullstring, lastword)
            if matches is None:
                return True
            if lastword:
                startstring = fullstring[: -len(lastword)]
            else:
                startstring = fullstring
            fullmatches = [startstring + m for m in matches]
            if len(fullmatches) == 1:
                self.setText(fullmatches[0])
            else:
                self._completer.setModel(QStringListModel(fullmatches, self))
                self._completer.complete()
            return True
        return QLineEdit.event(self, event)

    def keyPressEvent(self, kev):
        key_code = kev.key()

        # if it's a shifted scroll key...
        if (
            kev.modifiers() & Qt.KeyboardModifier.ShiftModifier
            and self.scrollWidget
            and key_code in self.scrollingKeys
        ):
            # create a new, unshifted key event and send it to the
            # scrolling widget
            nev = QKeyEvent(kev.type(), kev.key(), Qt.KeyboardModifier.NoModifier)
            QApplication.sendEvent(self.scrollWidget, nev)
            return

        if key_code == Qt.Key.Key_Escape:
            # abort history search
            self.setText(self._start_text)
            self._current = -1
            self.escapePressed.emit()
            QLineEdit.keyPressEvent(self, kev)

        elif key_code == Qt.Key.Key_Up:
            # go earlier
            if self._current == -1:
                self._start_text = self.text()
                self._current = len(self.history)
            self.stepHistory(-1)
        elif key_code == Qt.Key.Key_Down:
            # go later
            if self._current == -1:
                return
            self.stepHistory(1)

        elif key_code == Qt.Key.Key_PageUp:
            # go earlier with prefix
            if self._current == -1:
                self._current = len(self.history)
                self._start_text = self.text()
            prefix = self.text()[: self.cursorPosition()]
            self.stepHistoryUntil(prefix, "up")

        elif key_code == Qt.Key.Key_PageDown:
            # go later with prefix
            if self._current == -1:
                return
            prefix = self.text()[: self.cursorPosition()]
            self.stepHistoryUntil(prefix, "down")

        elif key_code == Qt.Key.Key_Return or key_code == Qt.Key.Key_Enter:
            # accept - add to history and do normal processing
            self._current = -1
            text = self.text()
            if text and (not self.history or self.history[-1] != text):
                # append to history, but only if it isn't equal to the last
                self.history.append(text)
            self._completer.setCompletionPrefix("")
            self._completer.setModel(QStringListModel([], self))
            QLineEdit.keyPressEvent(self, kev)

        else:
            # process normally
            QLineEdit.keyPressEvent(self, kev)

    def stepHistory(self, num):
        self._current += num
        if self._current <= -1:
            # no further
            self._current = 0
            return
        if self._current >= len(self.history):
            # back to start
            self._current = -1
            self.setText(self._start_text)
            return
        self.setText(self.history[self._current])

    def stepHistoryUntil(self, prefix, direction):
        if direction == "up":
            lookrange = range(self._current - 1, -1, -1)
        else:
            lookrange = range(self._current + 1, len(self.history))
        for i in lookrange:
            if self.history[i].startswith(prefix):
                self._current = i
                self.setText(self.history[i])
                self.setCursorPosition(len(prefix))
                return
        if direction == "down":
            # nothing found: go back to start
            self._current = -1
            self.setText(self._start_text)
            self.setCursorPosition(len(prefix))

    def setStatus(self, status):
        """Update with the daemon status."""
        self.current_status = status
        if status != "idle":
            setBackgroundColor(self, self.run_color)
            if not self.error_status:
                setForegroundColor(self, self.inactive_fgcolor)
        else:
            setBackgroundColor(self, self.idle_color)
            if not self.error_status:
                setForegroundColor(self, self.active_fgcolor)
        self.update()
        self.setEnabled(status != "disconnected")
        self.state = State.BUSY if status != "idle" else State.DEFAULT
        refresh_widget(self)

    def on_textChanged(self):
        setForegroundColor(self, self.active_fgcolor)
        try:
            script = self.text()
            if not script or script.strip().startswith("#"):
                return
            compile(script + "\n", "script", "single")
        except Exception:
            self.error_status = True
            setForegroundColor(self, self.error_fgcolor)
            self.update()
        else:
            self.error_status = False
            setForegroundColor(self, self.active_fgcolor)

    def on_returnPressed(self):
        script = self.text()
        if not script:
            return
        action = "queue"
        if self.current_status != "idle":
            qwindow = ScriptExecQuestion()
            result = qwindow.exec()
            if result == QMessageBox.StandardButton.Cancel:
                return
            elif result == QMessageBox.StandardButton.Apply:
                if self.current_status != "idle":
                    # if still busy try immediate execution, may raise,
                    # else just queue it
                    action = "execute"
        self.execRequested.emit(script, action)
