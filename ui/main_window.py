# ui/main_window.py
import sys, os, threading, asyncio
from PyQt6.QtWidgets import (
    QMainWindow, QWidget, QVBoxLayout, QHBoxLayout, QLabel, QPushButton,
    QListWidget, QListWidgetItem, QFrame, QMessageBox, QApplication, QSizePolicy, QMenu
)
from PyQt6.QtCore import QSize, Qt
from PyQt6.QtGui import QAction, QIcon, QCursor
from typing import cast
from ui.theme_manager import ThemeManager
from ui.dialogs.launch_editor import LaunchEditor       
from ui.dialogs.settings_dialog import SettingsDialog   
from core.app_settings import APP_SETTINGS
from core.launcher_logic import run_launch_sequence
from core.storage import load_launches, save_launches

APP_NAME = APP_SETTINGS["window_title"]

def get_icon(name: str) -> QIcon:
    base_dir = getattr(sys, "_MEIPASS", os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..")))
    return QIcon(os.path.join(base_dir, "resources", "icons", name))

class LaunchListRow(QWidget):
    def __init__(self, name, on_run, on_edit, on_delete):
        super().__init__()
        row = QHBoxLayout(self)
        self.edit_btn = QPushButton(); self.edit_btn.setIcon(get_icon("edit.svg"))
        self.name_btn = QPushButton(name)
        self.del_btn = QPushButton(); self.del_btn.setIcon(get_icon("delete.svg"))
        self.edit_btn.clicked.connect(on_edit)
        self.name_btn.clicked.connect(on_run)
        self.del_btn.clicked.connect(on_delete)
        for w in (self.edit_btn, self.name_btn, self.del_btn):
            w.setCursor(QCursor(Qt.CursorShape.PointingHandCursor))
        row.addWidget(self.edit_btn)
        row.addWidget(self.name_btn, 1)
        row.addWidget(self.del_btn)

class MainWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle(APP_NAME)
        self.resize(900, 620)
        self.launches = load_launches()

        # --- central widget and root layout ---
        central = QWidget()
        self.setCentralWidget(central)
        root = QVBoxLayout(central)
        root.setContentsMargins(0, 0, 0, 16)
        root.setSpacing(0)
        app_menu = cast(QMenu, self.menuBar().addMenu("File")) # type: ignore[reportOptionalMemberAccess]

        act_settings = QAction("Settings…", self)
        act_quit = QAction("Quit", self)
        app_menu.addAction(act_settings)
        app_menu.addSeparator()
        app_menu.addAction(act_quit)

        act_settings.triggered.connect(self._open_settings)
        act_quit.triggered.connect(self.close)

        # --- top dark bar ---
        self.top_bar = QFrame()
        self.top_bar.setFixedHeight(36)
        self.top_bar.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Fixed)
        self._apply_topbar_color()
        root.addWidget(self.top_bar)

        # --- content area ---
        content = QVBoxLayout()
        content.setContentsMargins(16, 12, 16, 16)
        content.setSpacing(12)
        root.addLayout(content, 1)

        # --- header row (title + add button) ---
        head = QHBoxLayout()
        title = QLabel("Launcher List")
        title.setStyleSheet("font-weight:600; font-size:16px;")
        head.addWidget(title)
        head.addStretch(1)

        self.add_btn = QPushButton()
        self.add_btn.setIcon(get_icon("add.svg"))
        self.add_btn.clicked.connect(self._add)
        head.addWidget(self.add_btn)
        content.addLayout(head)

        # --- launcher list ---
        self.listw = QListWidget()
        self.listw.setSpacing(8)
        self.listw.setUniformItemSizes(False)
        content.addWidget(self.listw, 1)

        self._refresh_list()

    def _apply_topbar_color(self):
        dark = ThemeManager.is_dark()
        color = "#1e1e1e" if dark else "#e0e0e0"
        self.top_bar.setStyleSheet(f"background-color: {color}; border:none;")

    def _refresh_list(self):
        self.listw.clear()
        for i, bundle in enumerate(self.launches):
            name = bundle.get("name", "Untitled")
            def make_cb(index=i):
                def run(): self._run_index(index)
                def edit(): self._edit_index(index)
                def delete(): self._delete_index(index)
                return run, edit, delete
            on_run, on_edit, on_delete = make_cb(i)
            item = QListWidgetItem()
            row = LaunchListRow(name, on_run, on_edit, on_delete)
            item.setSizeHint(QSize(0, 58))
            self.listw.addItem(item)
            self.listw.setItemWidget(item, row)

    def _add(self):
        def on_save(data):
            self.launches.append(data)
            save_launches(self.launches)
            self._refresh_list()
        dlg = LaunchEditor(on_save=on_save)
        dlg.exec()

    def _edit_index(self, i):
        def on_save(data):
            self.launches[i] = data
            save_launches(self.launches)
            self._refresh_list()
        dlg = LaunchEditor(existing=self.launches[i], on_save=on_save)
        dlg.exec()

    def _delete_index(self, i):
        name = self.launches[i].get("name", "Untitled")
        if QMessageBox.question(self, "Delete", f"Delete '{name}'?") == QMessageBox.StandardButton.Yes:
            self.launches.pop(i)
            save_launches(self.launches)
            self._refresh_list()

    def _run_index(self, i):
        bundle = self.launches[i]
        def worker():
            try:
                asyncio.run(run_launch_sequence(bundle["paths"]))
            except Exception as e:
                QMessageBox.critical(self, "Error", str(e))
        threading.Thread(target=worker, daemon=True).start()

    def _open_settings(self):
        def on_changed(v: bool):
            ThemeManager.set_dark(v)
            app = cast(QApplication, QApplication.instance())
            ThemeManager.apply(app, v)
            self._apply_topbar_color()

        dlg = SettingsDialog(self, dark=ThemeManager.is_dark(), on_changed=on_changed)
        dlg.exec()
