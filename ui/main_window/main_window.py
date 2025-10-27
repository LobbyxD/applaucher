# ui/main_window/main_window.py
from typing import cast

from PyQt6.QtCore import QSize, Qt, QTimer
from PyQt6.QtGui import QCursor
from PyQt6.QtWidgets import (QFrame, QHBoxLayout, QLabel, QListWidget,
                             QListWidgetItem, QMainWindow, QPushButton,
                             QVBoxLayout, QWidget)

from core.app_settings import APP_SETTINGS
from core.storage import load_launches
from ui.dialogs.launch_editor import LaunchEditor
from ui.icon_loader import themed_icon
# --- Local imports (after split) ---
from ui.main_window.actions import Actions
from ui.main_window.launch_worker import LaunchWorker
from ui.main_window.tray_manager import TrayManager
from ui.theme_manager import ThemeManager
from ui.widgets.style_helpers import (apply_frame_style, apply_label_style,
                                      apply_list_style)

APP_NAME = APP_SETTINGS["window_title"]

# --------------------------------------------------------------------------
# Row Widget for each launcher
# --------------------------------------------------------------------------
class LaunchListRow(QWidget):
    def __init__(self, name, on_run, on_edit, on_delete, on_export):
        super().__init__()
        layout = QHBoxLayout(self)
        self.edit_btn, self.name_btn, self.del_btn, self.export_btn = (
            QPushButton(), QPushButton(name), QPushButton(), QPushButton()
        )
        for w in (self.edit_btn, self.name_btn, self.del_btn, self.export_btn):
            w.setCursor(QCursor(Qt.CursorShape.PointingHandCursor))
        self.refresh_icons()
        ThemeManager.instance().theme_changed.connect(self.refresh_icons)
        self.edit_btn.clicked.connect(on_edit)
        self.name_btn.clicked.connect(on_run)
        self.del_btn.clicked.connect(on_delete)
        self.export_btn.clicked.connect(on_export)
        self.export_btn.setToolTip("Create Desktop Shortcut")
        layout.addWidget(self.edit_btn)
        layout.addWidget(self.name_btn, 1)
        layout.addWidget(self.export_btn)
        layout.addWidget(self.del_btn)
        
    def refresh_icons(self):
        self.edit_btn.setIcon(themed_icon("edit.svg"))
        self.del_btn.setIcon(themed_icon("delete.svg"))
        self.export_btn.setIcon(themed_icon("export.svg"))

# --------------------------------------------------------------------------
# Main Window
# --------------------------------------------------------------------------
class MainWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle(APP_NAME)
        self.resize(900, 620)
        self.launches = load_launches()

        # --- Create managers first ---
        self.action_mgr = Actions(self)
        self.tray = TrayManager(self)

        # --- Build UI (can now use action_mgr safely) ---
        self._build_ui()
        self._refresh_list()

        # --- Build menu AFTER managers exist ---
        self.action_mgr.build_menu(self.menuBar())

        # --- Connect signals ---
        ThemeManager.instance().theme_changed.connect(self.refresh_theme)

    # -----------------------------
    # UI SETUP
    # -----------------------------
    def _build_ui(self):
        central = QWidget()
        root = QVBoxLayout(central)
        root.setContentsMargins(16, 12, 16, 16)
        self.setCentralWidget(central)


        # Header
        header = QHBoxLayout()
        title = QLabel("Launcher List")
        apply_label_style(title, bold=True, size=24)
        self.add_btn = QPushButton()
        self.add_btn.setIcon(themed_icon("add.svg"))
        self.add_btn.setFixedSize(36, 36)
        self.add_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        self.add_btn.clicked.connect(self._add)
        header.addStretch(1)
        header.addWidget(title, alignment=Qt.AlignmentFlag.AlignCenter)
        header.addStretch(1)
        header.addWidget(self.add_btn, alignment=Qt.AlignmentFlag.AlignRight)
        root.addLayout(header)

        # List container
        list_container = QFrame()
        list_container.setObjectName("launcherListContainer")
        list_layout = QVBoxLayout(list_container)
        self.listw = QListWidget()
        apply_list_style(self.listw) 
        list_layout.addWidget(self.listw)
        root.addWidget(list_container, 1)
        apply_frame_style(list_container, "launcherListContainer")

        # Status bar
        self.status_label = QLabel("")
        self.status_label.setAlignment(Qt.AlignmentFlag.AlignRight)
        root.addWidget(self.status_label)

    # -----------------------------
    # THEME + STATUS
    # -----------------------------
    def refresh_theme(self, is_dark: bool):
        self.add_btn.setIcon(themed_icon("add.svg"))
        self.action_mgr.refresh_icons()
        for i in range(self.listw.count()):
            row = self.listw.itemWidget(self.listw.item(i))
            row.refresh_icons()
    def _show_message(self, text: str, duration: int = 3000):
        self.status_label.setText(text)
        QTimer.singleShot(duration, lambda: self.status_label.setText(""))

    # -----------------------------
    # LIST LOGIC
    # -----------------------------
    def _refresh_list(self):
        self.listw.clear()
        for i, bundle in enumerate(self.launches):
            name = bundle.get("name", "Untitled")
            make = lambda f, i=i: lambda _: f(i)
            row = LaunchListRow(
                name,
                make(self._run_index),
                make(self._edit_index),
                make(self._delete_index),
                make(self._export_index),
            )
            item = QListWidgetItem()
            item.setSizeHint(QSize(0, 58))
            self.listw.addItem(item)
            self.listw.setItemWidget(item, row)

    # -----------------------------
    # CRUD ACTIONS
    # -----------------------------
    def _add(self): self.action_mgr.add_launcher()
    def _edit_index(self, i): self.action_mgr.edit_launcher(i)
    def _delete_index(self, i): self.action_mgr.delete_launcher(i)
    def _export_index(self, i): self.action_mgr.export_shortcut(i)
    def _run_index(self, i): self.action_mgr.run_launcher(i)

    # -----------------------------
    # TRAY + EVENTS
    # -----------------------------
    # -----------------------------
    # TRAY + EVENTS
    # -----------------------------
    def changeEvent(self, e):
        """Propagate minimize/restore changes to dialogs safely."""
        if hasattr(self, "action_mgr"):  # ✅ guard for early init calls
            self.action_mgr.propagate_change_event(e)
        super().changeEvent(e)

    def closeEvent(self, e):
        """Handle minimize-to-tray logic safely."""
        if hasattr(self, "tray"):
            self.tray.handle_close_event(e)
        else:
            super().closeEvent(e)
