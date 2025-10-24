# ui/theme_manager.py
import os, json
from PyQt6.QtCore import QStandardPaths
from PyQt6.QtGui import QColor, QPalette
from PyQt6.QtWidgets import QApplication, QStyleFactory

class ThemeManager:
    SETTINGS_FILE = os.path.join(
        QStandardPaths.writableLocation(QStandardPaths.StandardLocation.AppDataLocation),
        "settings.json"
    )

    @staticmethod
    def _load() -> dict:
        if os.path.exists(ThemeManager.SETTINGS_FILE):
            try:
                with open(ThemeManager.SETTINGS_FILE, "r", encoding="utf-8") as f:
                    return json.load(f)
            except Exception:
                pass
        return {}

    @staticmethod
    def is_dark() -> bool:
        data = ThemeManager._load()
        return bool(data.get("dark", True))

    @staticmethod
    def set_dark(value: bool):
        os.makedirs(os.path.dirname(ThemeManager.SETTINGS_FILE), exist_ok=True)
        data = ThemeManager._load()
        data["dark"] = bool(value)
        with open(ThemeManager.SETTINGS_FILE, "w", encoding="utf-8") as f:
            json.dump(data, f, indent=2)

    @staticmethod
    def apply(app: QApplication, dark: bool):
        app.setStyle(QStyleFactory.create("Fusion"))
        p = QPalette()

        if dark:
            bg, base, text, btn, btn_text, border, hover = (
                "#1e1e1e", "#2a2a2a", "#e6e6e6", "#2a2a2a", "#e6e6e6", "#3a3a3a", "#333333"
            )
        else:
            bg, base, text, btn, btn_text, border, hover = (
                "#f5f5f5", "#ffffff", "#222222", "#ffffff", "#222222", "#d0d0d0", "#e6e6e6"
            )

        p.setColor(QPalette.ColorRole.Window, QColor(bg))
        p.setColor(QPalette.ColorRole.Base, QColor(base))
        p.setColor(QPalette.ColorRole.WindowText, QColor(text))
        p.setColor(QPalette.ColorRole.Button, QColor(btn))
        p.setColor(QPalette.ColorRole.ButtonText, QColor(btn_text))
        app.setPalette(p)

        app.setStyleSheet(f"""
        QWidget {{ font-size:14px; font-family:'Segoe UI'; color:{text}; }}
        QFrame#card {{ border-radius:10px; border:1px solid {border}; background:{base}; }}
        QPushButton {{ border:1px solid {border}; border-radius:8px; padding:8px 12px; background:{btn}; color:{btn_text}; }}
        QPushButton:hover {{ background:{hover}; }}
        """)
