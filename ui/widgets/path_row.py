# ui/widgets/path_row.py
import os
from typing import Any, Dict

from PyQt6 import sip
from PyQt6.QtCore import Qt
from PyQt6.QtWidgets import (QComboBox, QDoubleSpinBox, QFileDialog, QFrame,
                             QHBoxLayout, QLabel, QLineEdit, QPushButton,
                             QSizePolicy, QWidget)

from ui.icon_loader import themed_icon
from ui.theme_manager import ThemeManager

MODES = ["Normal", "Maximized", "Minimized"]

from PyQt6.QtCore import Qt
from PyQt6.QtGui import QColor, QPalette
from PyQt6.QtWidgets import QComboBox, QFrame, QListView

from ui.theme_manager import ThemeManager


class ThemedComboBox(QComboBox):
    """Theme-synced combo box with popup that truly matches App Launcher color scheme."""
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

        # Custom view for styling control
        view = QListView()
        view.setSpacing(2)
        view.setUniformItemSizes(True)
        view.setVerticalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        view.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        view.setEditTriggers(QListView.EditTrigger.NoEditTriggers)
        view.setFrameShape(QFrame.Shape.NoFrame)
        self.setView(view)

        self._apply_theme_colors()

    def _apply_theme_colors(self):
        """Applies ThemeManager colors directly to popup palette (ensures consistency)."""
        colors = ThemeManager.load_themes()["dark" if ThemeManager.is_dark() else "light"]

        base = QColor(colors["Base"])
        text = QColor(colors["Text"])
        window = QColor(colors["Window"])
        highlight = QColor(colors["Hover"])

        pal = self.palette()
        pal.setColor(QPalette.ColorRole.Base, base)
        pal.setColor(QPalette.ColorRole.Window, window)
        pal.setColor(QPalette.ColorRole.Text, text)
        pal.setColor(QPalette.ColorRole.ButtonText, text)
        pal.setColor(QPalette.ColorRole.Highlight, highlight)
        pal.setColor(QPalette.ColorRole.HighlightedText, text)
        self.setPalette(pal)

    def showPopup(self):
        """Ensure popup adopts theme palette and aligns perfectly with combo field."""
        self._apply_theme_colors()
        view = self.view()
        popup = view.window()

        # --- Ensure it's frameless, no drop shadow ---
        popup.setWindowFlags(
            Qt.WindowType.Popup
            | Qt.WindowType.FramelessWindowHint
            | Qt.WindowType.NoDropShadowWindowHint
        )

        # ✅ Make popup *truly transparent* under the styled QListView
        popup.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground, True)
        popup.setAttribute(Qt.WidgetAttribute.WA_StyledBackground, True)
        view.setFrameShape(QFrame.Shape.NoFrame)

        # --- Theme colors ---
        colors = ThemeManager.load_themes()["dark" if ThemeManager.is_dark() else "light"]
        border = colors["Border"]
        bg = colors["Base"]
        hover = colors["Hover"]
        text = colors["Text"]

        # --- Style the inner view only (not the popup window) ---
        view.setStyleSheet(f"""
            QListView {{
                background-color: {bg};
                border: 1px solid {border};
                border-radius: 8px;
                outline: none;
            }}
            QListView::item {{
                padding: 6px 10px;
                border-radius: 6px;
                color: {text};
            }}
            QListView::item:hover {{
                background-color: {hover};
            }}
            QListView::item:selected {{
                background-color: {hover};
                color: {text};
            }}
        """)

        # --- Align popup exactly under combo field ---
        field_rect = self.rect()
        global_pos = self.mapToGlobal(field_rect.bottomLeft())
        popup.move(global_pos.x(), global_pos.y() + 1)

        # --- Show popup first (creates the native window) ---
        super().showPopup()

        # --- Apply rounded mask to the popup ---
        from PyQt6.QtGui import QRegion, QPainterPath
        from PyQt6.QtCore import QRectF

        popup_rect = QRectF(popup.rect())
        radius = 8
        path = QPainterPath()
        path.addRoundedRect(popup_rect, radius, radius)
        region = QRegion(path.toFillPolygon().toPolygon())
        popup.setMask(region)




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
        self._apply_input_style(self.path_edit)

        # Browse button
        self.browse_btn = QPushButton()
        self.browse_btn.setIcon(themed_icon("folder.svg"))
        self.browse_btn.setToolTip("Browse for executable")
        self.browse_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        self.browse_btn.setFixedSize(32, 32)
        self._apply_button_style(self.browse_btn)

        # Delay spinbox
        self.delay = QDoubleSpinBox()
        self._apply_spinbox_style(self.delay)
        self.delay.setRange(0, 9999)
        self.delay.setDecimals(2)
        self.delay.setSuffix(" s")
        self.delay.setValue(float(delay))

        # Mode dropdown (frameless custom combo)
        self.mode = ThemedComboBox()
        self.mode.addItems(MODES)
        if mode in MODES:
            self.mode.setCurrentText(mode)

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
        self._apply_combobox_style(self.mode)


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
                    self._apply_button_style(self.browse_btn)
                if _is_alive(self.delete_btn):
                    self._apply_button_style(self.delete_btn)
                if _is_alive(self.mode):
                    self._apply_combobox_style(self.mode)

        ThemeManager.instance().theme_changed.connect(_safe_refresh)


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

    def _apply_input_style(self, input_field: QLineEdit):
        """Modern, theme-aware flat QLineEdit with readable selection."""
        colors = ThemeManager.load_themes()["dark" if ThemeManager.is_dark() else "light"]
        base = colors["Base"]
        hover = colors["Hover"]
        border = colors["Border"]
        text = colors["Text"]

        # Use contrasting text for selection depending on theme
        selection_bg = hover
        selection_text = "#ffffff" if ThemeManager.is_dark() else "#000000"

        input_field.setStyleSheet(f"""
            QLineEdit {{
                background-color: {base};
                border: 1px solid {border};
                border-radius: 6px;
                padding: 6px 8px;
                color: {text};
                selection-background-color: {selection_bg};
                selection-color: {selection_text};
                font-size: 13px;
            }}
            QLineEdit:hover {{
                border: 1px solid {hover};
            }}
            QLineEdit:focus {{
                border: 1px solid {hover};
                background-color: {base};
            }}
        """)

    def _apply_spinbox_style(self, spinbox: QDoubleSpinBox):
        """Modern, flat QDoubleSpinBox styled to match theme with readable selection."""
        colors = ThemeManager.load_themes()["dark" if ThemeManager.is_dark() else "light"]
        base = colors["Base"]
        hover = colors["Hover"]
        border = colors["Border"]
        text = colors["Text"]

        theme_dir = "dark" if ThemeManager.is_dark() else "light"
        arrow_up = os.path.join("resources", "icons", f"{theme_dir} icons", "spin_up.svg").replace("\\", "/")
        arrow_down = os.path.join("resources", "icons", f"{theme_dir} icons", "spin_down.svg").replace("\\", "/")

        selection_bg = hover
        selection_text = "#ffffff" if ThemeManager.is_dark() else "#000000"

        spinbox.setStyleSheet(f"""
            QDoubleSpinBox {{
                background-color: {base};
                border: 1px solid {border};
                border-radius: 6px;
                padding: 4px 22px 4px 8px; /* space for arrows */
                color: {text};
                font-size: 13px;
                selection-background-color: {selection_bg};
                selection-color: {selection_text};
            }}
            QDoubleSpinBox:hover {{
                border: 1px solid {hover};
            }}
            QDoubleSpinBox:focus {{
                border: 1px solid {hover};
                background-color: {base};
            }}
            QDoubleSpinBox::up-button {{
                subcontrol-origin: border;
                subcontrol-position: top right;
                width: 18px;
                border: none;
                background: transparent;
            }}
            QDoubleSpinBox::down-button {{
                subcontrol-origin: border;
                subcontrol-position: bottom right;
                width: 18px;
                border: none;
                background: transparent;
            }}
            QDoubleSpinBox::up-arrow {{
                image: url({arrow_up});
                width: 10px;
                height: 10px;
            }}
            QDoubleSpinBox::down-arrow {{
                image: url({arrow_down});
                width: 10px;
                height: 10px;
            }}
            QDoubleSpinBox::up-arrow:hover,
            QDoubleSpinBox::down-arrow:hover {{
                background-color: {hover};
                border-radius: 3px;
            }}
        """)

    def _apply_combobox_style(self, combo: QComboBox):
        """Final modern combo style consistent with App Launcher theme."""
        colors = ThemeManager.load_themes()["dark" if ThemeManager.is_dark() else "light"]
        base = colors["Base"]
        hover = colors["Hover"]
        border = colors["Border"]
        text = colors["Text"]
        window = colors["Window"]

        theme_dir = "dark" if ThemeManager.is_dark() else "light"
        arrow_down = os.path.join(
            "resources", "icons", f"{theme_dir} icons", "spin_down.svg"
        ).replace("\\", "/")

        combo.setStyleSheet(f"""
            /* === Combo Field === */
            QComboBox {{
                border: 1px solid {border};
                border-radius: 8px;
                padding: 6px 28px 6px 10px;
                color: {text};
                font-size: 13px;
            }}
            QComboBox:hover {{
                border: 1px solid {hover};
            }}
            QComboBox::drop-down {{
                subcontrol-origin: padding;
                subcontrol-position: top right;
                width: 22px;
                background: transparent;
            }}
            QComboBox::down-arrow {{
                image: url({arrow_down});
                width: 12px;
                height: 12px;
            }}

            /* === Popup view === */
            QComboBox QAbstractItemView {{
                border: 1px solid {border};
                border-radius: 8px;
                padding: 4px;
                margin-top: 3px;
                outline: none;
            }}

            /* === Items === */
            QComboBox QAbstractItemView::item {{
                padding: 6px 12px;
                border-radius: 6px;
                color: {text};
                background: transparent;
            }}
            QComboBox QAbstractItemView::item:hover {{
                background-color: {hover};
            }}
            QComboBox QAbstractItemView::item:selected {{
                background-color: {hover};
                color: {text};
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


