# main.py
import asyncio
import os
import sys

from PyQt6.QtGui import QIcon
from PyQt6.QtWidgets import QApplication

from core.app_settings import APP_SETTINGS
from core.launcher_logic import run_launch_sequence
from core.storage import (LAUNCHERS_FILE_NAME, get_data_path, load_launches,
                          save_launches)
from ui.main_window import MainWindow
from ui.theme_manager import ThemeManager


def run_direct_if_requested() -> bool:
    """If started with: --launch "<name>", run that launch and exit. Returns True if handled."""
    if len(sys.argv) >= 3 and sys.argv[1] == "--launch":
        from PyQt6.QtWidgets import QApplication, QMessageBox
        app = QApplication([])

        target = sys.argv[2]
        launches = load_launches()
        match = next((l for l in launches if l.get("name") == target), None)
        if not match:
            QMessageBox.warning(None, "App Launcher", f"No App Launch found named: {target}")
            return True

        try:
            asyncio.run(run_launch_sequence(match["paths"]))
        except Exception as e:
            QMessageBox.critical(None, "App Launcher", str(e))
        return True
    return False

if __name__ == "__main__":
    # Handle CLI “headless” mode first
    if run_direct_if_requested():
        sys.exit(0)

    app = QApplication(sys.argv)

        # === First-run setup ===


    # Ensure AppData directories & defaults exist
    ThemeManager.ensure_appdir()
    ThemeManager.ensure_default_themes()
    ThemeManager.ensure_default_settings()
    ThemeManager.lock_config_files()

    # Ensure launchers_config.json exists (using global name)
    launches_file = get_data_path()
    if not os.path.exists(launches_file):
        try:
            save_launches([])  # create empty file
        except Exception as e:
            print(f"⚠️ Could not initialize launch data: {e}")



    icon_path = os.path.join(os.path.dirname(__file__), APP_SETTINGS["icon_path"])
    if os.path.exists(icon_path):
        app.setWindowIcon(QIcon(icon_path))

    # Create main window first
    w = MainWindow()

    # 🔹 Now apply the saved theme (after widgets exist)
    theme_value = ThemeManager.get_setting("theme", "dark")
    ThemeManager.apply_theme(theme_value)

    w.show()

    # 🔹 Force a repaint of all widgets (ensures no residual flicker)
    for widget in app.topLevelWidgets():
        widget.update()
        widget.repaint()

    sys.exit(app.exec())
