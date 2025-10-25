# ui/icon_loader.py
import os
from PyQt6.QtGui import QIcon
from ui.theme_manager import ThemeManager

def themed_icon(name: str) -> QIcon:
    """
    Loads the correct icon (dark/light) based on current theme.
    Example: themed_icon("add.svg")
    """
    base_path = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "resources", "icons"))
    folder = "light icons" if ThemeManager.is_dark() else "dark icons"
    icon_path = os.path.join(base_path, folder, name)

    if not os.path.exists(icon_path):
        print(f"⚠️ Missing icon: {icon_path}")
        return QIcon()
    return QIcon(icon_path)
