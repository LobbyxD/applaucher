# ui/main_window/tray_manager.py
import os
import sys

from PyQt6.QtCore import Qt
from PyQt6.QtGui import QAction, QCloseEvent, QIcon
from PyQt6.QtWidgets import QApplication, QMenu, QSystemTrayIcon

from core.app_settings import APP_SETTINGS
from ui.theme_manager import ThemeManager

APP_NAME = APP_SETTINGS["window_title"]

class TrayManager:
    def __init__(self, window):
        self.window = window
        self.tray_icon = None
        self._setup()

    def _setup(self):
        icon_path = os.path.join(os.path.dirname(__file__), "..", "resources", "icons", "AppLauncher.ico")
        if not os.path.exists(icon_path) and getattr(sys, "frozen", False):
            if hasattr(sys, "_MEIPASS"):
                icon_path = os.path.join(sys._MEIPASS, "resources", "icons", "AppLauncher.ico")

        tray = QSystemTrayIcon(QIcon(icon_path), self.window)
        tray.setToolTip(APP_NAME)
        menu = QMenu()
        act_open = QAction("Open App", self.window)
        act_quit = QAction("Exit", self.window)
        menu.addAction(act_open)
        menu.addSeparator()
        menu.addAction(act_quit)
        tray.setContextMenu(menu)
        act_open.triggered.connect(self._restore_from_tray)
        act_quit.triggered.connect(QApplication.instance().quit)
        tray.activated.connect(self._on_activated)
        tray.show()
        self.tray_icon = tray

    def _on_activated(self, reason):
        if reason == QSystemTrayIcon.ActivationReason.Trigger:
            self._restore_from_tray()

    def _restore_from_tray(self):
        flags = self.window.windowFlags()
        flags &= ~Qt.WindowType.Tool
        flags |= Qt.WindowType.Window
        self.window.setWindowFlags(flags)
        self.window.setWindowFlag(Qt.WindowType.WindowStaysOnTopHint, False)
        self.window.showNormal()
        self.window.show()
        self.window.raise_()
        self.window.activateWindow()
        self.window.setWindowState(Qt.WindowState.WindowActive)

    def handle_close_event(self, event: QCloseEvent):
        minimize_to_tray = ThemeManager.get_setting("minimize_to_tray", False)
        if minimize_to_tray:
            event.ignore()
            self.window.hide()
            if self.tray_icon:
                self.tray_icon.showMessage(
                    APP_NAME,
                    "Application minimized to tray.",
                    QSystemTrayIcon.MessageIcon.Information,
                     2000
                )
        else:
            event.accept()
