# main.py
import asyncio
import os
import sys

from PyQt6.QtGui import QIcon
from PyQt6.QtWidgets import QApplication

from core.app_settings import APP_SETTINGS
from core.launcher_logic import run_launch_sequence
from core.storage import get_data_path, load_launches, save_launches
from ui.main_window.main_window import MainWindow
from ui.theme_manager import ThemeManager
from core.single_instance import SingleInstance


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


def focus_main_window(window):
    if not window:
        return

    window.showNormal()
    window.raise_()
    window.activateWindow()

    # 🔥 Windows-specific hard focus
    if sys.platform == "win32":
        from core.windows_focus import force_foreground
        hwnd = int(window.winId())
        force_foreground(hwnd)


if __name__ == "__main__":
    # Handle CLI “headless” mode first
    if run_direct_if_requested():
        sys.exit(0)

    app = QApplication(sys.argv)

    # 🔒 SINGLE INSTANCE ENFORCEMENT (RIGHT HERE)
    instance = SingleInstance()

    if instance.is_running():
        # Another instance exists → it was already focused
        sys.exit(0)

    # === First-run setup ===
    ThemeManager.ensure_appdir()
    ThemeManager.ensure_default_themes()
    ThemeManager.ensure_default_settings()
    ThemeManager.lock_config_files()

    launches_file = get_data_path()
    if not os.path.exists(launches_file):
        try:
            save_launches([])
        except Exception as e:
            print(f"⚠️ Could not initialize launch data: {e}")

    icon_path = os.path.join(os.path.dirname(__file__), APP_SETTINGS["icon_path"])
    if os.path.exists(icon_path):
        app.setWindowIcon(QIcon(icon_path))

    # ✅ Create main window
    w = MainWindow()

    # 🔁 Now that window exists — start listening for focus requests
    instance.start_server(lambda: focus_main_window(w))

    if os.path.exists(icon_path):
        w.setWindowIcon(QIcon(icon_path))

    theme_value = ThemeManager.get_setting("theme", "dark")
    ThemeManager.apply_theme(theme_value)

    w.show()

    for widget in app.topLevelWidgets():
        widget.update()
        widget.repaint()

    sys.exit(app.exec())

