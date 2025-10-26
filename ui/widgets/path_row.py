# ui/widgets/path_row.py
from typing import Any, Dict

from PyQt6 import sip
from PyQt6.QtCore import Qt
from PyQt6.QtWidgets import (QDoubleSpinBox, QFileDialog, QHBoxLayout, QLabel,
                             QLineEdit, QPushButton, QSizePolicy, QWidget)

from ui.icon_loader import themed_icon
from ui.theme_manager import ThemeManager
from ui.widgets.style_helpers import (apply_button_style, apply_combobox_style,
                                      apply_input_style, apply_spinbox_style)
from ui.widgets.themed_combobox import ThemedComboBox

MODES = ["Normal", "Maximized", "Minimized"]

# ui/widgets/path_row.py
class PathRow(QWidget):
    def __init__(self, path: str = "", delay: float = None, mode: str = None):
        super().__init__()
        self.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Maximum)
        # Give each row a subtle background for visibility
        colors = ThemeManager.load_themes()["dark" if ThemeManager.is_dark() else "light"]
        base = colors["Base"]
        alt = colors["Window"]  # usually slightly lighter/darker
        self.setStyleSheet("border-radius: 8px;")

        if delay is None:
            delay = float(ThemeManager.get_setting("default_delay", 0))
        if mode is None:
            default_state = ThemeManager.get_setting("default_window_state", "Normal")
            # Map stored 'Normal' → UI text 'Normal'
            mode = "Normal" if default_state == "Normal" else default_state

        # --- Widgets ---
        self.path_edit = QLineEdit(path)
        apply_input_style(self.path_edit)

        # Browse button
        self.browse_btn = QPushButton()
        self.browse_btn.setIcon(themed_icon("folder.svg"))
        self.browse_btn.setToolTip("Browse for executable")
        self.browse_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        self.browse_btn.setFixedSize(32, 32)
        apply_button_style(self.browse_btn)

        # Delay spinbox
        self.delay = QDoubleSpinBox()
        apply_spinbox_style(self.delay)
        self.delay.setRange(0, 9999)
        self.delay.setDecimals(2)
        self.delay.setSuffix(" s")
        self.delay.setValue(float(delay))

        # --- Mode dropdown (modern themed) ---
        self.mode = ThemedComboBox()
        self.mode.addItems(MODES)
        if mode in MODES:
            self.mode.setCurrentText(mode)

        # Improved size + font
        self.mode.setFixedHeight(30)
        self.mode.setMinimumWidth(120)
        self.mode.setCursor(Qt.CursorShape.PointingHandCursor)
        self.mode.setSizePolicy(QSizePolicy.Policy.Fixed, QSizePolicy.Policy.Fixed)

        # Apply theme styling
        apply_combobox_style(self.mode)

        # Delete button
        self.delete_btn = QPushButton()
        self.delete_btn.setIcon(themed_icon("delete.svg"))
        self.delete_btn.setToolTip("Delete this path")
        self.delete_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        self.delete_btn.setFixedSize(32, 32)
        apply_button_style(self.delete_btn)

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
            def _is_alive(widget):
                try:
                    return widget is not None and not sip.isdeleted(widget)
                except Exception:
                    return False

            def _safe_refresh(_=None):
                # Prevent invalid access after destruction
                if not _is_alive(self):
                    return
                if _is_alive(self.browse_btn):
                    apply_button_style(self.browse_btn)
                if _is_alive(self.delete_btn):
                    apply_button_style(self.delete_btn)
                if _is_alive(self.mode):
                    apply_combobox_style(self.mode)

        ThemeManager.instance().theme_changed.connect(_safe_refresh)


    def _refresh_button_styles(self):
        """Reapply button colors when theme toggles."""
        for btn in (self.browse_btn, self.delete_btn):
            apply_button_style(btn)

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
