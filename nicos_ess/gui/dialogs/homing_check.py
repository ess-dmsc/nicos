from nicos.guisupport.qt import QDialog, QDialogButtonBox, QLabel, QVBoxLayout


class HomingCheckDialog(QDialog):
    def __init__(self, message="Are you sure?"):
        QDialog.__init__(self)
        self.message = message

        buttons = (
            QDialogButtonBox.StandardButton.Ok | QDialogButtonBox.StandardButton.Cancel
        )
        button_box = QDialogButtonBox(buttons)
        button_box.accepted.connect(self.accept)
        button_box.rejected.connect(self.reject)
        layout = QVBoxLayout()
        message = QLabel(self.message)
        layout.addWidget(message)
        layout.addWidget(button_box)
        self.setLayout(layout)
