# ui/widgets/path_row.py
from PyQt6.QtWidgets import QWidget, QHBoxLayout, QLabel, QLineEdit, QPushButton, QDoubleSpinBox, QComboBox, QFileDialog
from typing import Dict, Any

MODES = ["Not Maximized", "Maximized", "Minimized"]

class PathRow(QWidget):
    def __init__(self, path="", delay=0.0, mode="Not Maximized"):
        super().__init__()
        self.path_edit = QLineEdit(path)
        self.browse_btn = QPushButton("📁")
        self.delay = QDoubleSpinBox()
        self.delay.setRange(0, 9999)
        self.delay.setDecimals(2)
        self.delay.setSuffix(" s")
        self.delay.setValue(float(delay))
        self.mode = QComboBox()
        self.mode.addItems(MODES)
        if mode in MODES:
            self.mode.setCurrentText(mode)
        self.delete_btn = QPushButton("🗑")

        row = QHBoxLayout(self)
        row.addWidget(QLabel("☰"))
        row.addWidget(self.path_edit, 1)
        row.addWidget(self.browse_btn)
        row.addWidget(QLabel("Delay:"))
        row.addWidget(self.delay)
        row.addWidget(QLabel("Mode:"))
        row.addWidget(self.mode)
        row.addWidget(self.delete_btn)
        self.browse_btn.clicked.connect(self._pick)

    def _pick(self):
        f, _ = QFileDialog.getOpenFileName(
            self, "Choose Executable", "", "Executables (*.exe *.bat *.cmd *.lnk);;All files (*.*)"
        )
        if f:
            self.path_edit.setText(f)

    def value(self) -> Dict[str, Any]:
        return {
            "path": self.path_edit.text().strip(),
            "delay": float(self.delay.value()),
            "start_option": self.mode.currentText(),
        }
