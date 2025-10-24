# main.py
import sys, os, asyncio
from PyQt6.QtWidgets import QApplication
from PyQt6.QtGui import QIcon
from core.app_settings import APP_SETTINGS
from core.storage import load_launches
from core.launcher_logic import run_launch_sequence
from ui.main_window import MainWindow
from ui.theme_manager import ThemeManager

print("🧩 sys.argv =", sys.argv, flush=True)


def run_direct_if_requested() -> bool:
    """If started with: --launch "<name>", run that launch and exit. Returns True if handled."""
    if len(sys.argv) >= 3 and sys.argv[1] == "--launch":
        from PyQt6.QtWidgets import QMessageBox, QApplication
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

    # --- Normal UI startup below ---
    app = QApplication(sys.argv)

    icon_path = os.path.join(os.path.dirname(__file__), APP_SETTINGS["icon_path"])
    if os.path.exists(icon_path):
        app.setWindowIcon(QIcon(icon_path))

    ThemeManager.apply(app, ThemeManager.is_dark())

    w = MainWindow()
    w.show()

    sys.exit(app.exec())
