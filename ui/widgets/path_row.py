# ui/widgets/path_row.py
from PyQt6.QtWidgets import (
    QWidget, QHBoxLayout, QLabel, QLineEdit, QPushButton,
    QDoubleSpinBox, QComboBox, QFileDialog
)
from PyQt6.QtCore import Qt
from typing import Dict, Any
from ui.icon_loader import themed_icon
from ui.theme_manager import ThemeManager

MODES = ["Not Maximized", "Maximized", "Minimized"]


# ui/widgets/path_row.py
# ...
class PathRow(QWidget):
    def __init__(self, path: str = "", delay: float = 0.0, mode: str = "Not Maximized"):
        super().__init__()

        # --- Widgets ---
        self.path_edit = QLineEdit(path)

        # Browse button
        self.browse_btn = QPushButton()
        self.browse_btn.setIcon(themed_icon("folder.svg"))
        self.browse_btn.setToolTip("Browse for executable")
        self.browse_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        self.browse_btn.setFixedSize(32, 32)
        self.browse_btn.setStyleSheet("border: none; border-radius: 6px; padding: 4px;")

        # Delay spinbox
        self.delay = QDoubleSpinBox()
        self.delay.setRange(0, 9999)
        self.delay.setDecimals(2)
        self.delay.setSuffix(" s")
        self.delay.setValue(float(delay))

        # Mode dropdown
        self.mode = QComboBox()
        self.mode.addItems(MODES)
        if mode in MODES:
            self.mode.setCurrentText(mode)

        # Delete button
        self.delete_btn = QPushButton()
        self.delete_btn.setIcon(themed_icon("delete.svg"))
        self.delete_btn.setToolTip("Delete this path")
        self.delete_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        self.delete_btn.setFixedSize(32, 32)
        self.delete_btn.setStyleSheet("border: none; border-radius: 6px; padding: 4px;")

        # --- Layout ---
        row = QHBoxLayout(self)
        row.setContentsMargins(2, 0, 2, 0)
        row.setSpacing(6)

        # --- Drag handle icon ---
        self.drag_lbl = QLabel()  # ✅ define after layout created
        self.drag_lbl.setToolTip("Drag to reorder")
        self.drag_lbl.setAlignment(Qt.AlignmentFlag.AlignCenter)
        drag_icon = themed_icon("bars.svg")
        self.drag_lbl.setPixmap(drag_icon.pixmap(16, 16))
        row.addWidget(self.drag_lbl)

        row.addWidget(self.path_edit, 1)
        row.addWidget(self.browse_btn)
        row.addWidget(QLabel("Delay:"))
        row.addWidget(self.delay)
        row.addWidget(QLabel("Mode:"))
        row.addWidget(self.mode)
        row.addWidget(self.delete_btn)

        # --- Behavior ---
        self.browse_btn.clicked.connect(self._pick)

        if hasattr(ThemeManager, "instance"):
            ThemeManager.instance().theme_changed.connect(self.refresh_icons)

    def refresh_icons(self, is_dark: bool):
        self.browse_btn.setIcon(themed_icon("folder.svg"))
        self.delete_btn.setIcon(themed_icon("delete.svg"))
        if getattr(self, "drag_lbl", None):
            self.drag_lbl.setPixmap(themed_icon("bars.svg").pixmap(16, 16))

    def _pick(self):
        f, _ = QFileDialog.getOpenFileName(
            self,
            "Choose Executable",
            "",
            "Executables (*.exe *.bat *.cmd *.lnk);;All files (*.*)"
        )
        if f:
            self.path_edit.setText(f)

    def value(self) -> Dict[str, Any]:
        return {
            "path": self.path_edit.text().strip(),
            "delay": float(self.delay.value()),
            "start_option": self.mode.currentText(),
        }
