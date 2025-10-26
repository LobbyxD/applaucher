# ui/dialogs/settings_dialog.py
import os

from PyQt6.QtCore import Qt
from PyQt6.QtGui import QAction, QCloseEvent, QCursor, QIcon
from PyQt6.QtWidgets import (QApplication, QComboBox, QDialog, QDoubleSpinBox,
                             QFrame, QHBoxLayout, QLabel, QListWidget,
                             QListWidgetItem, QMainWindow, QMenu, QMessageBox,
                             QPushButton, QSizePolicy, QSpacerItem,
                             QSystemTrayIcon, QVBoxLayout, QWidget)

from ui.widgets.toggle_switch import ToggleSwitch

from ..theme_manager import ThemeManager

ICON_SUN = os.path.join("resources", "icons", "light icons", "sun.png")
ICON_MOON = os.path.join("resources", "icons", "dark icons", "moon.svg")


class SettingsDialog(QDialog):
    def __init__(self, parent=None, dark: bool = True, on_changed=None):
        super().__init__(parent)
        SettingsDialog.refresh_settings_cache()
        self.setWindowTitle("Settings")
        self.setModal(True)
        self.setFixedWidth(460)
        self.on_changed = on_changed

        # === Root layout ===
        root = QVBoxLayout(self)
        root.setContentsMargins(18, 18, 18, 18)
        root.setSpacing(14)

        # === Section: Appearance ===
        appearance_card = self._create_section("Appearance")
        appearance_card.setStyleSheet("background: transparent;")

        theme_row = QHBoxLayout()
        theme_label = QLabel("Theme")
        theme_label.setStyleSheet("font-size:14px; font-weight:500; background: transparent;")
        theme_row.addWidget(theme_label)
        theme_row.addStretch()

        is_dark = ThemeManager.is_dark()
        self.theme_switch = ToggleSwitch(
            on_icon=ICON_MOON,
            off_icon=ICON_SUN,
            initial_state=is_dark
        )
        self.theme_switch.clicked.connect(self.toggle_theme)
        theme_row.addWidget(self.theme_switch)
        appearance_card.layout().addLayout(theme_row)

        # === Section: Launch Defaults ===
        launch_card = self._create_section("Launch Defaults")
        launch_card.setStyleSheet("background: transparent;")

        # Default Window State
        state_row = QHBoxLayout()
        state_label = QLabel("Default Window State")
        state_label.setStyleSheet("font-size:14px; font-weight:500; background: transparent;")
        state_row.addWidget(state_label)
        state_row.addStretch()
        self.state_combo = QComboBox()
        self.state_combo.addItems(["Normal", "Maximized", "Minimized"])
        current_state = ThemeManager.get_setting("default_window_state", "Normal")
        self.state_combo.setCurrentText(current_state)
        self.state_combo.currentTextChanged.connect(
            lambda v: ThemeManager.set_setting("default_window_state", v)
        )
        self.state_combo.setFixedWidth(160)
        state_row.addWidget(self.state_combo)
        launch_card.layout().addLayout(state_row)

        # Default Delay
        delay_row = QHBoxLayout()
        delay_label = QLabel("Default Delay Between Apps")
        delay_label.setStyleSheet("font-size:14px; font-weight:500; background: transparent;")
        delay_row.addWidget(delay_label)
        delay_row.addStretch()
        self.delay_spin = QDoubleSpinBox()
        self.delay_spin.setRange(0, 9999)
        self.delay_spin.setSuffix(" sec")
        self.delay_spin.setDecimals(0)
        self.delay_spin.setSingleStep(1)
        current_delay = ThemeManager.get_setting("default_delay", 0)
        self.delay_spin.setValue(int(current_delay))

        def _normalize_delay():
            val = self.delay_spin.value()
            rounded = int(round(val))
            self.delay_spin.setValue(rounded)
            ThemeManager.set_setting("default_delay", rounded)

        self.delay_spin.editingFinished.connect(_normalize_delay)
        self.delay_spin.setFixedWidth(100)
        delay_row.addWidget(self.delay_spin)
        launch_card.layout().addLayout(delay_row)

        # === Minimize to Tray ===
        tray_row = QHBoxLayout()
        tray_label = QLabel("Minimize to Tray on Close")
        tray_label.setStyleSheet("font-size:14px; font-weight:500; background: transparent;")
        tray_row.addWidget(tray_label)
        tray_row.addStretch()

        current_tray = ThemeManager.get_setting("minimize_to_tray", False)
        self.tray_switch = ToggleSwitch(initial_state=current_tray)
        self.tray_switch.clicked.connect(
            lambda: ThemeManager.set_setting("minimize_to_tray", self.tray_switch.isChecked())
        )
        tray_row.addWidget(self.tray_switch)
        launch_card.layout().addLayout(tray_row)

        # === Debug Logging (On/Off) ===
        log_row = QHBoxLayout()
        log_label = QLabel("Debug Logging")
        log_label.setStyleSheet("font-size:14px; font-weight:500; background: transparent;")
        log_row.addWidget(log_label)
        log_row.addStretch()

        current_debug = ThemeManager.get_setting("debug_logging", True)  # default ON
        self.debug_switch = ToggleSwitch(initial_state=current_debug)
        self.debug_switch.clicked.connect(
            lambda: ThemeManager.set_setting("debug_logging", self.debug_switch.isChecked())
        )
        log_row.addWidget(self.debug_switch)
        launch_card.layout().addLayout(log_row)


        # === Assemble main view ===
        root.addWidget(appearance_card)
        root.addWidget(launch_card)
        root.addSpacerItem(QSpacerItem(0, 10, QSizePolicy.Policy.Minimum, QSizePolicy.Policy.Expanding))

        # === Footer ===
        footer = QHBoxLayout()
        footer.addStretch()

        # --- Open Settings Folder Button ---
        open_folder_btn = QPushButton("Open Settings Folder")
        open_folder_btn.setFixedWidth(180)
        open_folder_btn.setCursor(QCursor(Qt.CursorShape.PointingHandCursor))
        open_folder_btn.clicked.connect(self._open_settings_folder)
        footer.addWidget(open_folder_btn)

        # --- Close Button ---
        close_btn = QPushButton("Close")
        close_btn.setFixedWidth(100)
        close_btn.clicked.connect(self.accept)
        footer.addWidget(close_btn)
        root.addLayout(footer)

         # === Theme-aware Styling (Fixed + Auto-refresh) ===
        def apply_theme_styles():
            all_themes = ThemeManager.load_themes()
            dark = ThemeManager.is_dark()
            colors = all_themes["dark" if dark else "light"]

            # Color references
            bg_card = colors["Window"] if not dark else "#252525"
            border = colors["Border"]
            text = colors["Text"]
            hover = colors["Hover"]
            button = colors["Button"]
            button_text = colors["ButtonText"]

            # === Determine correct arrow icons ===
            theme_dir = "dark" if dark else "light"
            up_arrow = os.path.join("resources", "icons", f"{theme_dir} icons", "spin_up.svg").replace("\\", "/")
            down_arrow = os.path.join("resources", "icons", f"{theme_dir} icons", "spin_down.svg").replace("\\", "/")

            # Use only supported Qt properties (no transition, shadow, or blur)
            self.setStyleSheet(f"""
                QDialog {{
                    background-color: {colors["Base"]};
                    border: none;
                }}
                /* --- Card Containers --- */
                QFrame#SectionCard {{
                    background-color: {bg_card};
                    border: 1px solid {border};
                    border-radius: 12px;
                    margin-bottom: 14px;
                    padding: 10px 16px;
                }}
                QLabel#SectionTitle {{
                    color: {text};
                    font-weight: 600;
                    font-size: 15px;
                    padding-bottom: 4px;
                }}
                QFrame#SectionUnderline {{
                    background-color: {hover};
                    border: none;
                    height: 2px;
                    border-radius: 1px;
                    margin-bottom: 8px;
                }}
                QLabel {{
                    color: {text};
                }}
                /* --- Form Controls --- */
                QComboBox, QDoubleSpinBox {{
                    background-color: {button};
                    border: 1px solid {border};
                    border-radius: 8px;
                    padding: 4px 10px;
                    min-height: 30px;
                    color: {button_text};
                }}
                QComboBox:hover, QDoubleSpinBox:hover {{
                    border: 1px solid {hover};
                }}
                QPushButton {{
                    background-color: {button};
                    color: {button_text};
                    border: 1px solid {border};
                    border-radius: 8px;
                    padding: 6px 16px;
                    font-weight: 500;
                }}
                QPushButton:hover {{
                    background-color: {hover};
                }}
                QDoubleSpinBox::up-button, QDoubleSpinBox::down-button {{
                    width: 18px;
                    border: none;
                    background: transparent;
                }}
                QDoubleSpinBox::up-arrow {{
                    image: url({up_arrow});
                    width: 10px;
                    height: 10px;
                }}
                QDoubleSpinBox::down-arrow {{
                    image: url({down_arrow});
                    width: 10px;
                    height: 10px;
                }}
                QDoubleSpinBox::up-button:hover,
                QDoubleSpinBox::down-button:hover {{
                    background-color: {hover};
                    border-radius: 6px;
                }}
            """)

        # Apply now
        apply_theme_styles()

        # React to future theme changes (dark/light toggle)
        if hasattr(ThemeManager, "instance"):
            ThemeManager.instance().theme_changed.connect(lambda _: apply_theme_styles())


    # === Helper: Create section wrapper ===
    def _create_section(self, title: str) -> QFrame:
        """Clean modern section with clear separation using native Qt visuals."""
        card = QFrame()
        card.setObjectName("SectionCard")

        layout = QVBoxLayout(card)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(10)

        # Header row
        title_label = QLabel(title)
        title_label.setObjectName("SectionTitle")
        title_label.setStyleSheet("font-weight: 700; text-decoration: underline;")
        layout.addWidget(title_label)

        underline = QFrame()
        underline.setObjectName("SectionUnderline")
        underline.setFrameShape(QFrame.Shape.HLine)
        underline.setFrameShadow(QFrame.Shadow.Plain)
        underline.setFixedHeight(2)
        layout.addWidget(underline)

        return card

    # === Open Settings Folder ===
    def _open_settings_folder(self):
        """Opens the directory containing settings.json, themes.json, and log.txt."""
        from PyQt6.QtGui import QDesktopServices
        from PyQt6.QtCore import QUrl
        from ui.theme_manager import ThemeManager

        ThemeManager.ensure_appdir()
        folder = ThemeManager.APP_DIR
        if os.path.exists(folder):
            QDesktopServices.openUrl(QUrl.fromLocalFile(folder))
        else:
            QMessageBox.warning(
                self,
                "Folder Missing",
                "Settings folder could not be found."
            )

    # === Toggle Theme Logic ===
    def toggle_theme(self):
        new_theme = "dark" if self.theme_switch.isChecked() else "light"
        ThemeManager.set_setting("theme", new_theme)
        ThemeManager.apply_theme(new_theme)
        if self.on_changed:
            self.on_changed(new_theme == "dark")

    @staticmethod
    def refresh_settings_cache():
        """Force reload from disk, ignoring cache."""
        ThemeManager._cached_settings = None
        ThemeManager._load_settings()
