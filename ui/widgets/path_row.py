# ui/widgets/path_row.py
from typing import Any, Dict

from PyQt6.QtCore import QEvent, Qt
from PyQt6.QtWidgets import (QComboBox, QDoubleSpinBox, QFileDialog,
                             QHBoxLayout, QLabel, QLineEdit, QPushButton,
                             QWidget, QSizePolicy)

from ui.icon_loader import themed_icon
from ui.theme_manager import ThemeManager

MODES = ["Not Maximized", "Maximized", "Minimized"]


# ui/widgets/path_row.py
class PathRow(QWidget):
    def __init__(self, path: str = "", delay: float = None, mode: str = None):
        super().__init__()
        self.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Maximum)
        # Give each row a subtle background for visibility
        colors = ThemeManager.load_themes()["dark" if ThemeManager.is_dark() else "light"]
        base = colors["Base"]
        alt = colors["Window"]  # usually slightly lighter/darker
        self.setStyleSheet(f"background-color: {alt}; border-radius: 8px;")

        if delay is None:
            delay = float(ThemeManager.get_setting("default_delay", 0))
        if mode is None:
            default_state = ThemeManager.get_setting("default_window_state", "Normal")
            # Map stored 'Normal' → UI text 'Not Maximized'
            mode = "Not Maximized" if default_state == "Normal" else default_state

        # --- Widgets ---
        self.path_edit = QLineEdit(path)

        # Browse button
        self.browse_btn = QPushButton()
        self.browse_btn.setIcon(themed_icon("folder.svg"))
        self.browse_btn.setToolTip("Browse for executable")
        self.browse_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        self.browse_btn.setFixedSize(32, 32)
        self._apply_button_style(self.browse_btn)

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
        self._apply_button_style(self.delete_btn)

        # --- Layout ---
        row = QHBoxLayout(self)
        row.setContentsMargins(2, 0, 2, 0)
        row.setSpacing(6)

        # --- Drag handle icon ---
        self.drag_lbl = QLabel()
        self.drag_lbl.setToolTip("Drag to reorder")
        self.drag_lbl.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.drag_lbl.setCursor(Qt.CursorShape.OpenHandCursor)  # ← grab cursor on hover
        self.drag_lbl.setStyleSheet("background: transparent;")  # keep clean bg
        self.drag_lbl.installEventFilter(self)                   # ← handle press/release

        drag_icon = themed_icon("bars.svg")
        self.drag_lbl.setPixmap(drag_icon.pixmap(16, 16))
        row.addWidget(self.drag_lbl)

        delay_label = QLabel("Delay:")
        delay_label.setStyleSheet("background: transparent;")
        mode_label = QLabel("Mode:")
        mode_label.setStyleSheet("background: transparent;")
        row.addWidget(self.path_edit, 1)
        row.addWidget(self.browse_btn)
        row.addWidget(delay_label)
        row.addWidget(self.delay)
        row.addWidget(mode_label)
        row.addWidget(self.mode)
        row.addWidget(self.delete_btn)
        self.setLayout(row)

        # --- Behavior ---
        self.browse_btn.clicked.connect(self._pick)

        if hasattr(ThemeManager, "instance"):
            ThemeManager.instance().theme_changed.connect(self.refresh_icons)
            ThemeManager.instance().theme_changed.connect(lambda _: self._refresh_button_styles())

    def _refresh_button_styles(self):
        """Reapply button colors when theme toggles."""
        for btn in (self.browse_btn, self.delete_btn):
            self._apply_button_style(btn)

    def refresh_icons(self, is_dark: bool):
        self.browse_btn.setIcon(themed_icon("folder.svg"))
        self.delete_btn.setIcon(themed_icon("delete.svg"))
        if getattr(self, "drag_lbl", None):
            self.drag_lbl.setPixmap(themed_icon("bars.svg").pixmap(16, 16))

        # === Shared Styling Helper (theme-aware) ===
    def _apply_button_style(self, btn: QPushButton):
        """Apply a consistent border, radius, and hover color to PathRow buttons."""
        colors = ThemeManager.load_themes()["dark" if ThemeManager.is_dark() else "light"]
        border = colors["Border"]
        hover = colors["Hover"]
        base = colors["Button"]
        text = colors["ButtonText"]

        btn.setStyleSheet(f"""
            QPushButton {{
                border: 1px solid {border};
                border-radius: 6px;
                background-color: {base};
                color: {text};
                padding: 4px;
            }}
            QPushButton:hover {{
                background-color: {hover};
            }}
        """)


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
