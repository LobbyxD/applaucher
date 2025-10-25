import json
import os
from PyQt6.QtCore import QObject, QStandardPaths, pyqtSignal
from PyQt6.QtGui import QColor, QPalette
from PyQt6.QtWidgets import QApplication, QStyleFactory, QWidget


class ThemeManager(QObject):
    theme_changed = pyqtSignal(bool)  # emits True if dark, False if light
    _instance = None

    APP_DIR = os.path.join(
        QStandardPaths.writableLocation(QStandardPaths.StandardLocation.AppDataLocation),
        "App Launcher"
    )

    SETTINGS_FILE = os.path.join(APP_DIR, "settings.json")
    THEMES_FILE = os.path.join(APP_DIR, "themes.json")

    DEFAULT_THEMES = {
        "dark": {
            "Window": "#1e1e1e",
            "Base": "#2a2a2a",
            "Text": "#e6e6e6",
            "Button": "#2a2a2a",
            "ButtonText": "#e6e6e6",
            "Border": "#3a3a3a",
            "Hover": "#333333"
        },
        "light": {
            "Window": "#e9e9e9",
            "Base": "#f2f2f2",
            "Text": "#202020",
            "Button": "#f5f5f5",
            "ButtonText": "#202020",
            "Border": "#c0c0c0",
            "Hover": "#d9d9d9"
        }
    }

    def __new__(cls):
        if cls._instance is None:
            cls._instance = super().__new__(cls)
        return cls._instance

    @staticmethod
    def instance():
        return ThemeManager._instance or ThemeManager()

    # === AppData folder helpers ===
    @staticmethod
    def ensure_appdir():
        """Ensure %APPDATA%/App Launcher/ exists."""
        os.makedirs(ThemeManager.APP_DIR, exist_ok=True)

    @staticmethod
    def ensure_default_themes():
        """If themes.json doesn’t exist, create it with defaults."""
        ThemeManager.ensure_appdir()
        if not os.path.exists(ThemeManager.THEMES_FILE):
            with open(ThemeManager.THEMES_FILE, "w", encoding="utf-8") as f:
                json.dump(ThemeManager.DEFAULT_THEMES, f, indent=2)

    # === Settings I/O ===
    @staticmethod
    def _load_settings() -> dict:
        ThemeManager.ensure_appdir()
        if os.path.exists(ThemeManager.SETTINGS_FILE):
            try:
                with open(ThemeManager.SETTINGS_FILE, "r", encoding="utf-8") as f:
                    return json.load(f)
            except Exception:
                pass
        return {}

    @staticmethod
    def _save_settings(data: dict):
        ThemeManager.ensure_appdir()
        with open(ThemeManager.SETTINGS_FILE, "w", encoding="utf-8") as f:
            json.dump(data, f, indent=2)

    @staticmethod
    def get_setting(key, default=None):
        data = ThemeManager._load_settings()
        return data.get(key, default)

    @staticmethod
    def set_setting(key, value):
        data = ThemeManager._load_settings()
        data[key] = value
        ThemeManager._save_settings(data)

    # === Theme I/O ===
    @staticmethod
    def load_themes() -> dict:
        """Load themes from AppData/themes.json; create defaults if missing."""
        ThemeManager.ensure_default_themes()
        try:
            with open(ThemeManager.THEMES_FILE, "r", encoding="utf-8") as f:
                return json.load(f)
        except Exception as e:
            print(f"⚠️ Failed to load themes.json: {e}")
            return ThemeManager.DEFAULT_THEMES.copy()

    @staticmethod
    def is_dark() -> bool:
        """Return True if current theme is dark."""
        data = ThemeManager._load_settings()
        theme_value = data.get("theme", "dark")
        return theme_value.lower() == "dark"

    @staticmethod
    def set_dark(value: bool):
        ThemeManager.ensure_appdir()
        data = ThemeManager._load_settings()
        data["theme"] = "dark" if value else "light"
        ThemeManager._save_settings(data)
        ThemeManager.instance().theme_changed.emit(value)

    # === Core application logic ===
    @staticmethod
    def apply(app: QApplication, dark: bool):
        """Apply theme dynamically."""
        app.setStyle(QStyleFactory.create("Fusion"))
        palette = QPalette()

        all_themes = ThemeManager.load_themes()
        colors = all_themes["dark" if dark else "light"]

        # Apply palette roles
        palette.setColor(QPalette.ColorRole.Window, QColor(colors["Window"]))
        palette.setColor(QPalette.ColorRole.Base, QColor(colors["Base"]))
        palette.setColor(QPalette.ColorRole.WindowText, QColor(colors["Text"]))
        palette.setColor(QPalette.ColorRole.Text, QColor(colors["Text"]))
        palette.setColor(QPalette.ColorRole.Button, QColor(colors["Button"]))
        palette.setColor(QPalette.ColorRole.ButtonText, QColor(colors["ButtonText"]))
        palette.setColor(QPalette.ColorRole.Highlight, QColor(colors["Hover"]))
        app.setPalette(palette)

        # Global stylesheet
        app.setStyleSheet(f"""
            * {{
                font-size: 14px;
                font-family: 'Segoe UI';
                color: {colors["Text"]};
            }}
            QMainWindow, QWidget {{
                background-color: {colors["Base"]};
            }}
            QMenuBar, QMenu {{
                background-color: {colors["Window"]};
                color: {colors["Text"]};
                border: none;
            }}
            QMenu::item:selected {{
                background-color: {colors["Hover"]};
            }}
            QFrame#card {{
                border-radius: 10px;
                border: 1px solid {colors["Border"]};
                background-color: {colors["Base"]};
            }}
            QPushButton {{
                border: 1px solid {colors["Border"]};
                border-radius: 8px;
                padding: 8px 12px;
                background-color: {colors["Button"]};
                color: {colors["ButtonText"]};
            }}
            QPushButton:hover {{
                background-color: {colors["Hover"]};
            }}
        """)

        # Force refresh
        for top in app.topLevelWidgets():
            for child in top.findChildren(QWidget):
                child.setPalette(palette)
            top.setPalette(palette)
            top.update()
            top.repaint()

    @staticmethod
    def apply_theme(theme: str):
        """Accepts 'dark' or 'light' and applies instantly."""
        app = QApplication.instance()
        if not app:
            return
        is_dark = theme.lower() == "dark"
        ThemeManager.apply(app, dark=is_dark)
        ThemeManager.set_setting("theme", theme)
        ThemeManager.instance().theme_changed.emit(is_dark)
