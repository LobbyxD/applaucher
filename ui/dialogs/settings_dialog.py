# ui/dialogs/settings_dialog.py
from PyQt6.QtWidgets import QDialog, QFrame, QVBoxLayout, QHBoxLayout, QLabel, QPushButton, QCheckBox
from PyQt6.QtCore import Qt

class SettingsDialog(QDialog):
    def __init__(self, parent=None, dark: bool = True, on_changed=None):
        super().__init__(parent)
        self.setWindowTitle("Settings")
        self.setModal(True)
        self.on_changed = on_changed

        card = QFrame()
        card.setObjectName("card")
        row = QHBoxLayout(card)
        row.setContentsMargins(16, 16, 16, 16)

        label = QLabel("Dark Mode")
        self.toggle = QCheckBox()
        self.toggle.setChecked(dark)
        row.addWidget(label)
        row.addStretch(1)
        row.addWidget(self.toggle)

        close = QPushButton("Close")
        layout = QVBoxLayout(self)
        layout.addWidget(card)
        layout.addWidget(close, alignment=Qt.AlignmentFlag.AlignRight)

        close.clicked.connect(self.accept)
        self.toggle.stateChanged.connect(self._apply)

    def _apply(self):
        if self.on_changed:
            self.on_changed(bool(self.toggle.isChecked()))
