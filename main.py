# main.py
import sys, os
from PyQt6.QtWidgets import QApplication
from PyQt6.QtGui import QIcon
from ui.main_window import MainWindow
from ui.theme_manager import ThemeManager
from core.app_settings import APP_SETTINGS

def main():
    app = QApplication(sys.argv)
    icon_path = os.path.join(os.path.dirname(__file__), APP_SETTINGS["icon_path"])
    if os.path.exists(icon_path):
        app.setWindowIcon(QIcon(icon_path))
    ThemeManager.apply(app, ThemeManager.is_dark())
    w = MainWindow()
    w.show()
    sys.exit(app.exec())

if __name__ == "__main__":
    main()
