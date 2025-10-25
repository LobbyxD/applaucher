# ui/dialogs/settings_dialog.py
from PyQt6.QtWidgets import (
    QDialog, QFrame, QVBoxLayout, QHBoxLayout,
    QLabel, QPushButton
)
from PyQt6.QtCore import QStandardPaths
from PyQt6.QtCore import Qt
from ui.widgets.toggle_switch import ToggleSwitch
from ..theme_manager import ThemeManager
import os, json
from PyQt6.QtWidgets import QComboBox, QDoubleSpinBox


# Icon paths
ICON_SUN = os.path.join("resources", "icons", "light icons", "sun.png")
ICON_MOON = os.path.join("resources", "icons", "dark icons", "moon.svg")


class SettingsDialog(QDialog):
    def __init__(self, parent=None, dark: bool = True, on_changed=None):
        super().__init__(parent)
        SETTINGS_FILE = os.path.join(
                QStandardPaths.writableLocation(QStandardPaths.StandardLocation.AppDataLocation),
                "App Launcher",
                "settings.json"
            )
        self.setWindowTitle("Settings")
        self.setModal(True)
        self.on_changed = on_changed

        # === Main Layout ===
        main_layout = QVBoxLayout(self)
        main_layout.setContentsMargins(20, 20, 20, 20)
        main_layout.setSpacing(16)

        # === Card Frame ===
        card = QFrame()
        card.setObjectName("card")
        card.setFrameShape(QFrame.Shape.StyledPanel)
        card_layout = QVBoxLayout(card)
        card_layout.setContentsMargins(20, 20, 20, 20)
        card_layout.setSpacing(12)

        # === THEME SECTION ===
        theme_row = QHBoxLayout()
        theme_row.setContentsMargins(0, 0, 0, 0)
        theme_label = QLabel("Theme")
        theme_label.setStyleSheet("font-size: 14px; background: transparent;")
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
        card_layout.addLayout(theme_row)

        # === DEFAULT WINDOW STATE ===
        state_row = QHBoxLayout()
        state_label = QLabel("Default Window State")
        state_label.setStyleSheet("font-size: 14px; background: transparent;")
        state_row.addWidget(state_label)
        state_row.addStretch()
        self.state_combo = QComboBox()
        self.state_combo.addItems(["Normal", "Maximized", "Minimized"])
        current_state = ThemeManager.get_setting("default_window_state", "Normal")
        self.state_combo.setCurrentText(current_state)
        self.state_combo.currentTextChanged.connect(
            lambda v: ThemeManager.set_setting("default_window_state", v)
        )
        state_row.addWidget(self.state_combo)
        card_layout.addLayout(state_row)

        # === DEFAULT DELAY BETWEEN APPS ===
        delay_row = QHBoxLayout()
        delay_label = QLabel("Default Delay Between Apps")
        delay_label.setStyleSheet("font-size: 14px; background: transparent;")
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
        delay_row.addWidget(self.delay_spin)
        card_layout.addLayout(delay_row)


        # === Footer Buttons ===
        close_btn = QPushButton("Close")
        close_btn.clicked.connect(self.accept)

        # === Assemble ===
        main_layout.addWidget(card)
        main_layout.addWidget(close_btn, alignment=Qt.AlignmentFlag.AlignRight)

        # Optional styling (depends on your theme system)
        self.setStyleSheet("""
            QDialog {
                background-color: palette(base);
            }
            #card {
                background-color: palette(window);
                border-radius: 8px;
            }
            QPushButton {
                padding: 6px 16px;
            }
        """)
        
    # === Toggle Theme Logic ===
    def toggle_theme(self):
        # ON = dark, OFF = light
        new_theme = "dark" if self.theme_switch.isChecked() else "light"

        ThemeManager.set_setting("theme", new_theme)
        ThemeManager.apply_theme(new_theme)

        if self.on_changed:
            self.on_changed(new_theme == "dark")
