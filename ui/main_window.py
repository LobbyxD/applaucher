# ui/main_window.py
import sys, os, threading, asyncio, re
from PyQt6.QtWidgets import (
    QMainWindow, QWidget, QVBoxLayout, QHBoxLayout, QLabel, QPushButton,
    QListWidget, QListWidgetItem, QFrame, QMessageBox, QApplication, QSizePolicy, QMenu
)
from PyQt6.QtCore import QSize, Qt, QTimer
from PyQt6.QtGui import QAction, QIcon, QCursor
from typing import cast
from ui.theme_manager import ThemeManager
from ui.dialogs.launch_editor import LaunchEditor       
from ui.dialogs.settings_dialog import SettingsDialog   
from core.app_settings import APP_SETTINGS
from core.launcher_logic import run_launch_sequence
from core.storage import load_launches, save_launches
from PyQt6.QtCore import QStandardPaths
from win32com.client import Dispatch
import pythoncom
from ui.icon_loader import themed_icon


def _sanitize_filename(name: str) -> str:
    # Windows-invalid chars: <>:"/\|?*
    return re.sub(r'[<>:"/\\|?*]', "_", name).strip()



APP_NAME = APP_SETTINGS["window_title"]

def get_icon(name: str) -> QIcon:
    """Return a QIcon with correct path resolution for both dev and frozen builds."""
    if getattr(sys, 'frozen', False) and hasattr(sys, '_MEIPASS'):
        # Running from PyInstaller bundle
        base_dir = sys._MEIPASS
    else:
        # Running from source (VSCode, Python directly)
        # Only go ONE level up from /ui/ to reach /resources/
        base_dir = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
    
    icon_path = os.path.join(base_dir, "resources", "icons", name)
    if not os.path.exists(icon_path):
        print(f"⚠️ Missing icon: {icon_path}")
    return QIcon(icon_path)


class LaunchListRow(QWidget):
    def __init__(self, name, on_run, on_edit, on_delete, on_export):
        super().__init__()
        row = QHBoxLayout(self)

        self.edit_btn = QPushButton()
        self.name_btn = QPushButton(name)
        self.del_btn = QPushButton()
        self.export_btn = QPushButton()

        # Assign icons dynamically based on theme
        self.refresh_icons()

        # Connect theme signal once
        ThemeManager.instance().theme_changed.connect(self.refresh_icons)

        # Wire actions
        self.edit_btn.clicked.connect(on_edit)
        self.name_btn.clicked.connect(on_run)
        self.del_btn.clicked.connect(on_delete)
        self.export_btn.clicked.connect(on_export)

        self.export_btn.setToolTip("Create Desktop Shortcut")

        for w in (self.edit_btn, self.name_btn, self.del_btn, self.export_btn):
            w.setCursor(QCursor(Qt.CursorShape.PointingHandCursor))

        row.addWidget(self.edit_btn)
        row.addWidget(self.name_btn, 1)
        row.addWidget(self.export_btn)
        row.addWidget(self.del_btn)

    def refresh_icons(self):
        self.edit_btn.setIcon(themed_icon("edit.svg"))
        self.del_btn.setIcon(themed_icon("delete.svg"))
        self.export_btn.setIcon(themed_icon("export.svg"))

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
        self.add_btn.setIcon(themed_icon("add.svg"))
        self.add_btn.clicked.connect(self._add)
        head.addWidget(self.add_btn)
        content.addLayout(head)

        ThemeManager.instance().theme_changed.connect(self.refresh_theme)

        # --- launcher list ---
        self.listw = QListWidget()
        self.listw.setSpacing(8)
        self.listw.setUniformItemSizes(False)
        content.addWidget(self.listw, 1)

        # --- status message label (bottom of list) ---
        self.status_label = QLabel("")
        self.status_label.setAlignment(Qt.AlignmentFlag.AlignRight)
        self.status_label.setStyleSheet("font-size:12px; opacity:0.7; padding-right:6px;")
        content.addWidget(self.status_label)

        self._refresh_list()

    def refresh_theme(self, is_dark: bool):
        """Reapply icons and colors when theme toggles."""
        self.add_btn.setIcon(themed_icon("add.svg"))
        self._apply_topbar_color()
        for i in range(self.listw.count()):
            item = self.listw.item(i)
            row = self.listw.itemWidget(item)
            if hasattr(row, "refresh_icons"):
                row.refresh_icons()

    def _show_message(self, text: str, duration: int = 3000):
        """Show a small fading status message."""
        self.status_label.setText(text)
        self.status_label.setStyleSheet(
            "font-size:12px; opacity:1.0; padding-right:6px;"
        )
        QTimer.singleShot(duration, lambda: self.status_label.setText(""))

    def _apply_topbar_color(self):
        dark = ThemeManager.is_dark()
        color = "#1e1e1e" if dark else "#e0e0e0"
        self.top_bar.setStyleSheet(f"background-color: {color}; border:none;")

    def _refresh_list(self):
        self.listw.clear()

        for i, bundle in enumerate(self.launches):
            name = bundle.get("name", "Untitled")

            # define handlers as normal functions to lock the index
            def make_handler(func, index):
                return lambda _, f=func, i=index: f(i)

            row = LaunchListRow(
                name,
                make_handler(self._run_index, i),
                make_handler(self._edit_index, i),
                make_handler(self._delete_index, i),
                make_handler(self._export_index, i),
            )

            item = QListWidgetItem()
            item.setSizeHint(QSize(0, 58))
            self.listw.addItem(item)
            self.listw.setItemWidget(item, row)



    def _add(self):
        def on_save(data):
            self.launches.append(data)
            save_launches(self.launches)
            self._refresh_list()
            self._show_message(f"Created {data.get('name', 'Untitled')} successfully.")
        dlg = LaunchEditor(on_save=on_save)
        dlg.exec()

    def _edit_index(self, i):
        def on_save(data):
            self.launches[i] = data
            save_launches(self.launches)
            self._refresh_list()
            self._show_message(f"{data.get('name', 'Untitled')} Updated.")
        dlg = LaunchEditor(existing=self.launches[i], on_save=on_save)
        dlg.exec()

    def _delete_index(self, i):
        """Handle delete with inline confirmation instead of QMessageBox."""
        # Initialize persistent flag
        if not hasattr(self, "_delete_pending"):
            self._delete_pending = None

        if self._delete_pending == i:
            # second click confirms deletion
            name = self.launches[i].get("name", "Untitled")
            self.launches.pop(i)
            save_launches(self.launches)
            self._refresh_list()
            self._show_message(f"Deleted {name} successfully.")
            self._delete_pending = None
        else:
            # first click asks for confirmation
            self._delete_pending = i
            self._show_message("⚠️ Click delete again to confirm.")

    def _export_index(self, i):
        """Create a Windows .lnk desktop shortcut for this App Launch."""
        try:
            bundle = self.launches[i]
            name = bundle.get("name", "Untitled").strip() or "Untitled"
            safe = _sanitize_filename(name)

            # Desktop path (OneDrive-safe)
            desktop = QStandardPaths.writableLocation(QStandardPaths.StandardLocation.DesktopLocation)
            if not desktop or not os.path.exists(desktop):
                desktop = os.path.join(os.path.expanduser("~"), "Desktop")

            # ✅ MUST end with .lnk
            shortcut_path = os.path.join(desktop, f"{safe}.lnk")

            # Target + args + icon depending on frozen vs source
            if getattr(sys, "frozen", False):
                # Frozen: AppLauncher.exe --launch "Name"
                target = sys.executable
                arguments = f'--launch "{name}"'
                working_dir = os.path.dirname(sys.executable)

                # Try bundled icon (MEIPASS-safe)
                icon_path = os.path.join(working_dir, "resources", "icons", "AppLauncher.ico")
                if not os.path.exists(icon_path) and hasattr(sys, "_MEIPASS"):
                    icon_path = os.path.join(sys._MEIPASS, "resources", "icons", "AppLauncher.ico")
            else:
                # Source: python main.py --launch "Name"
                target = sys.executable
                main_py = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "main.py"))
                arguments = f'"{main_py}" --launch "{name}"'
                working_dir = os.path.dirname(main_py)
                icon_path = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "resources", "icons", "AppLauncher.ico"))

            # Initialize COM for this thread
            pythoncom.CoInitialize()
            try:
                shell = Dispatch("WScript.Shell")
                shortcut = shell.CreateShortcut(shortcut_path)
                shortcut.TargetPath = target
                shortcut.Arguments = arguments
                shortcut.WorkingDirectory = working_dir
                shortcut.WindowStyle = 1  # normal window
                shortcut.Description = f"Launch '{name}' with {APP_NAME}"
                if os.path.exists(icon_path):
                    # ,0 is the icon index in the file
                    shortcut.IconLocation = f"{icon_path},0"
                shortcut.save()
            finally:
                pythoncom.CoUninitialize()

            self._show_message(f"Desktop shortcut created: {os.path.basename(safe)}")
        except Exception as e:
            # No QMessageBox — inline status only
            self._show_message(f"❌ Export failed: {e}")


    def _run_index(self, i):
        bundle = self.launches[i]
        def worker():
            try:
                asyncio.run(run_launch_sequence(bundle["paths"]))
                self._show_message(f"{bundle['name']} Launched.")
            except Exception as e:
                self._show_message(f"❌ Error: {e}.")
        threading.Thread(target=worker, daemon=True).start()

    def _open_settings(self):
        def on_changed(v: bool):
            ThemeManager.set_dark(v)
            app = cast(QApplication, QApplication.instance())
            ThemeManager.apply(app, v)
            self._apply_topbar_color()

        dlg = SettingsDialog(self, dark=ThemeManager.is_dark(), on_changed=on_changed)
        dlg.exec()
