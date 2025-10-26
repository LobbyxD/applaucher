# ui/main_window.py
import json
import os
import re
import sys
from typing import cast

import pythoncom
from PyQt6.QtCore import (QObject, QSize, QStandardPaths, Qt, QThread, QTimer,
                          pyqtSignal)
from PyQt6.QtGui import QAction, QCloseEvent, QCursor, QIcon
from PyQt6.QtWidgets import (QApplication, QFileDialog, QFrame, QHBoxLayout,
                             QLabel, QListWidget, QListWidgetItem, QMainWindow,
                             QMenu, QPushButton, QSystemTrayIcon, QVBoxLayout,
                             QWidget, QDialog)
from win32com.client import Dispatch

from core.app_settings import APP_SETTINGS
from core.storage import load_launches, save_launches
from ui.dialogs.launch_editor import LaunchEditor
from ui.dialogs.settings_dialog import SettingsDialog
from ui.icon_loader import themed_icon
from ui.theme_manager import ThemeManager


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

# --- Qt worker that runs the async sequence off the GUI thread ---
class LaunchWorker(QObject):
    progress = pyqtSignal(str)   # status text
    finished = pyqtSignal(str)   # final message

    def __init__(self, apps, launch_name: str):
        super().__init__()
        self.apps = apps
        self.launch_name = launch_name

    def run(self):
        """Run the async launch sequence inside its own event loop."""
        import asyncio

        from core.launcher_logic import run_launch_sequence

        def _emit(text: str, **_):
            # progress_cb from launcher_logic sometimes passes end="\r"
            self.progress.emit(text)

        try:
            loop = asyncio.new_event_loop()
            asyncio.set_event_loop(loop)
            loop.run_until_complete(run_launch_sequence(self.apps, progress_cb=_emit))
        except Exception as e:
            # Bubble a concise error back to UI
            self.finished.emit(f"❌ Error: {e}")
            return
        finally:
            try:
                loop.close()
            except Exception:
                pass

        self.finished.emit(f"{self.launch_name} Launched.")

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
        self._apply_menu_style()


        act_settings = QAction("Settings…", self)
        act_quit = QAction("Quit", self)
        app_menu.addAction(act_settings)
        app_menu.addSeparator()
        app_menu.addAction(act_quit)

        # --- Import / Export Launchers (theme-aware) ---
        self.act_import = QAction("Import Launchers…", self)
        self.act_export = QAction("Export Launchers…", self)

        self.act_import.setIcon(themed_icon("import.svg"))
        self.act_export.setIcon(themed_icon("export.svg"))

        app_menu.addAction(self.act_import)
        app_menu.addAction(self.act_export)
        app_menu.addSeparator()
        app_menu.addAction(act_settings)
        app_menu.addSeparator()
        app_menu.addAction(act_quit)

        self.act_import.triggered.connect(self._import_launchers)
        self.act_export.triggered.connect(self._export_launchers)


        act_settings.triggered.connect(self._open_settings)
        act_quit.triggered.connect(self.close)

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

        # --- launcher list container (theme-aware border) ---
        list_container = QFrame()
        list_container.setObjectName("launcherListContainer")
        list_layout = QVBoxLayout(list_container)
        list_layout.setContentsMargins(6, 6, 6, 6)
        list_layout.setSpacing(0)

        self.listw = QListWidget()
        self.listw.setSpacing(8)
        self.listw.setUniformItemSizes(False)
        self.listw.setFrameShape(QFrame.Shape.NoFrame)
        self.listw.setFrameShadow(QFrame.Shadow.Plain)

        list_layout.addWidget(self.listw)
        content.addWidget(list_container, 1)

        self._apply_list_container_style(list_container)
        ThemeManager.instance().theme_changed.connect(lambda _: self._apply_list_container_style(list_container))

        # --- status message label (bottom of list) ---
        self.status_label = QLabel("")
        self.status_label.setAlignment(Qt.AlignmentFlag.AlignRight)
        self.status_label.setStyleSheet("font-size:12px; opacity:0.7; padding-right:6px;")
        content.addWidget(self.status_label)

        self._refresh_list()

        # === Tray Icon Setup ===
        self.tray_icon = None
        self._setup_tray_icon()


    def refresh_theme(self, is_dark: bool):
        """Reapply icons and colors when theme toggles."""
        self._apply_menu_style()

        # Header buttons
        self.add_btn.setIcon(themed_icon("add.svg"))

        # Menu actions (Import / Export)
        if hasattr(self, "act_import"):
            self.act_import.setIcon(themed_icon("import.svg"))
        if hasattr(self, "act_export"):
            self.act_export.setIcon(themed_icon("export.svg"))

        # List rows
        for i in range(self.listw.count()):
            item = self.listw.item(i)
            row = self.listw.itemWidget(item)
            if hasattr(row, "refresh_icons"):
                row.refresh_icons()

    def _apply_menu_style(self):
        """Apply theme-aware bottom border to menu bar."""
        all_themes = ThemeManager.load_themes()
        dark = ThemeManager.is_dark()
        colors = all_themes["dark" if dark else "light"]

        border = colors["Border"]
        bg = colors["Window"]
        text = colors["Text"]
        hover = colors["Hover"]

        self.menuBar().setStyleSheet(f"""
            QMenuBar {{
                background-color: {bg};
                color: {text};
                border: none;
                border-bottom: 1px solid {border};
            }}
            QMenuBar::item:selected {{
                background-color: {hover};
            }}
            QMenu {{
                background-color: {bg};
                color: {text};
                border: 1px solid {border};
            }}
            QMenu::item:selected {{
                background-color: {hover};
            }}
        """)

    def _apply_list_container_style(self, container: QFrame):
        """Apply theme-based border + background for launcher list area."""
        colors = ThemeManager.load_themes()["dark" if ThemeManager.is_dark() else "light"]
        border = colors["Border"]
        base = colors["Base"]
        hover = colors["Hover"]

        container.setStyleSheet(f"""
            QFrame#launcherListContainer {{
                border: 1px solid {border};
                border-radius: 8px;
                background-color: {base};
                margin-top: 4px;
            }}
            QFrame#launcherListContainer:hover {{
                border: 1px solid {hover};
            }}
        """)


    def _show_message(self, text: str, duration: int = 3000):
        """Show a small fading status message."""
        self.status_label.setText(text)
        self.status_label.setStyleSheet(
            "font-size:12px; opacity:1.0; padding-right:6px;"
        )
        QTimer.singleShot(duration, lambda: self.status_label.setText(""))

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

        dlg = LaunchEditor(on_save=on_save, parent=self)
        dlg.setWindowModality(Qt.WindowModality.WindowModal)
        dlg.setWindowFlag(Qt.WindowType.Dialog, True)
        dlg.setWindowFlag(Qt.WindowType.Window, False)
        dlg.setWindowFlag(Qt.WindowType.SubWindow, True)
        dlg.setWindowFlag(Qt.WindowType.WindowStaysOnTopHint, False)
        dlg.setWindowFlag(Qt.WindowType.Tool, True)
        dlg.show()
        dlg.raise_()
        dlg.activateWindow()

        # The minimize/restore sync is handled via changeEvent() override.


    def _edit_index(self, i):
        def on_save(data):
            self.launches[i] = data
            save_launches(self.launches)
            self._refresh_list()
            self._show_message(f"{data.get('name', 'Untitled')} Updated.")

        dlg = LaunchEditor(existing=self.launches[i], on_save=on_save, parent=self)
        dlg.setWindowModality(Qt.WindowModality.WindowModal)
        dlg.setWindowFlag(Qt.WindowType.Dialog, True)
        dlg.setWindowFlag(Qt.WindowType.Window, False)
        dlg.setWindowFlag(Qt.WindowType.SubWindow, True)
        dlg.setWindowFlag(Qt.WindowType.WindowStaysOnTopHint, False)
        dlg.setWindowFlag(Qt.WindowType.Tool, True)
        dlg.show()
        dlg.raise_()
        dlg.activateWindow()

        # The minimize/restore sync is handled via changeEvent() override.

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
        """Run the selected launcher in a QThread and stream progress back via signals."""
        bundle = self.launches[i]
        name = bundle.get("name", "Untitled")

        # 1) Build worker + thread
        self._launch_thread = QThread(self)
        self._launch_worker = LaunchWorker(bundle["paths"], name)
        self._launch_worker.moveToThread(self._launch_thread)

        # 2) Wire signals
        self._launch_thread.started.connect(self._launch_worker.run)
        self._launch_worker.progress.connect(self._show_message)
        self._launch_worker.finished.connect(self._on_launch_finished)

        # 3) Ensure clean teardown
        self._launch_worker.finished.connect(self._launch_thread.quit)
        self._launch_thread.finished.connect(self._launch_worker.deleteLater)
        self._launch_thread.finished.connect(self._launch_thread.deleteLater)

        # 4) Go!
        self._launch_thread.start()

    def _on_launch_finished(self, msg: str):
        # Display final status (success or error)
        self._show_message(msg, duration=3000)

    def _open_settings(self):
        def on_changed(v: bool):
            ThemeManager.set_dark(v)
            app = cast(QApplication, QApplication.instance())
            ThemeManager.apply(app, v)

        dlg = SettingsDialog(self, dark=ThemeManager.is_dark(), on_changed=on_changed)
        dlg.exec()

        # === Tray Logic ===
    def _setup_tray_icon(self):
        """Initialize tray icon and its context menu."""
        icon_path = os.path.join(os.path.dirname(__file__), "..", "resources", "icons", "AppLauncher.ico")
        if not os.path.exists(icon_path) and getattr(sys, "frozen", False):
            # PyInstaller safe path
            if hasattr(sys, "_MEIPASS"):
                icon_path = os.path.join(sys._MEIPASS, "resources", "icons", "AppLauncher.ico")

        tray_icon = QSystemTrayIcon(QIcon(icon_path), self)
        tray_icon.setToolTip(APP_NAME)

        menu = QMenu()
        act_open = QAction("Open App", self)
        act_quit = QAction("Exit", self)
        menu.addAction(act_open)
        menu.addSeparator()
        menu.addAction(act_quit)

        act_open.triggered.connect(self._restore_from_tray)
        act_quit.triggered.connect(QApplication.instance().quit)

        tray_icon.setContextMenu(menu)
        tray_icon.activated.connect(self._on_tray_activated)
        tray_icon.show()

        self.tray_icon = tray_icon

    def _on_tray_activated(self, reason):
        """Handle click events on tray icon."""
        if reason == QSystemTrayIcon.ActivationReason.Trigger:
            self._restore_from_tray()

    def _restore_from_tray(self):
        """Fully restore main window and make it visible on the Windows taskbar."""
        # If window was hidden, ensure it is re-registered as a normal window
        flags = self.windowFlags()
        # Remove Tool and Frameless flags if they were implicitly set by Qt
        flags &= ~Qt.WindowType.Tool
        flags |= Qt.WindowType.Window
        self.setWindowFlags(flags)

        # Explicitly show in taskbar again (Qt.WindowStaysOnTopHint fix)
        self.setWindowFlag(Qt.WindowType.WindowStaysOnTopHint, False)

        # Apply and show
        self.showNormal()
        self.show()           # ensures visibility
        self.raise_()
        self.activateWindow()

        # Re-add it to taskbar (Windows only)
        self.setWindowState(Qt.WindowState.WindowActive)

        # === Import/Export Launchers ===
    def _export_launchers(self):
        """Export current to chosen location."""

        downloads = QStandardPaths.writableLocation(QStandardPaths.StandardLocation.DownloadLocation)
        if not downloads or not os.path.exists(downloads):
            downloads = os.path.expanduser("~/Downloads")

        file_path, _ = QFileDialog.getSaveFileName(
            self,
            "Export Launchers",
            os.path.join(downloads, "launches_export.json"),
            "JSON Files (*.json)"
        )

        if not file_path:
            return

        try:
            with open(file_path, "w", encoding="utf-8") as f:
                json.dump(self.launches, f, indent=2)
            self._show_message(f"✅ Launchers exported to: {os.path.basename(file_path)}")
        except Exception as e:
            self._show_message(f"❌ Export failed: {e}")

    def _import_launchers(self):
        """Import launchers from chosen .json file."""
        import json

        from PyQt6.QtWidgets import QFileDialog, QMessageBox

        file_path, _ = QFileDialog.getOpenFileName(
            self,
            "Import Launchers",
            "",
            "JSON Files (*.json)"
        )
        if not file_path:
            return

        try:
            with open(file_path, "r", encoding="utf-8") as f:
                imported = json.load(f)
        except Exception as e:
            QMessageBox.critical(self, "Invalid File", f"Failed to read file:\n{e}")
            return

        # --- Validate schema ---
        if not isinstance(imported, list):
            QMessageBox.critical(self, "Invalid Format", "JSON root must be a list of launchers.")
            return

        def _is_valid_launcher(item: dict) -> bool:
            return (
                isinstance(item, dict)
                and "name" in item
                and isinstance(item["name"], str)
                and "paths" in item
                and isinstance(item["paths"], list)
                and all(
                    isinstance(p, dict)
                    and "path" in p
                    and "delay" in p
                    and "start_option" in p
                    for p in item["paths"]
                )
            )

        if not all(_is_valid_launcher(x) for x in imported):
            QMessageBox.critical(self, "Invalid Structure", "One or more launchers are malformed.")
            return

        # --- Ask user to Merge or Replace ---
        msg = QMessageBox(self)
        msg.setWindowTitle("Import Launchers")
        msg.setText("Do you want to merge with existing launchers, or replace them?")
        msg.setIcon(QMessageBox.Icon.Question)

        # Add custom buttons
        merge_btn = msg.addButton("Merge", QMessageBox.ButtonRole.YesRole)
        replace_btn = msg.addButton("Replace", QMessageBox.ButtonRole.NoRole)
        cancel_btn = msg.addButton("Cancel", QMessageBox.ButtonRole.RejectRole)

        # Default selected button
        msg.setDefaultButton(merge_btn)

        # Show dialog
        msg.exec()

        # Handle result (same logic you had before)
        if msg.clickedButton() == cancel_btn:
            return
        elif msg.clickedButton() == merge_btn:
            # Merge (avoid duplicates by name)
            existing_names = {x.get("name") for x in self.launches}
            merged = self.launches + [x for x in imported if x.get("name") not in existing_names]
            self.launches = merged
        elif msg.clickedButton() == replace_btn:
            # Replace
            self.launches = imported


        # Save and refresh UI
        save_launches(self.launches)
        self._refresh_list()
        if msg.clickedButton() == merge_btn:
            self._show_message("✅ Launchers imported successfully.")
        elif msg.clickedButton() == replace_btn:
            self._show_message("✅ Launchers replaced successfully.")

    def changeEvent(self, event):
        """Sync minimize/restore state to all child dialogs like LaunchEditor."""
        from PyQt6.QtCore import QEvent
        if event.type() == QEvent.Type.WindowStateChange:
            is_minimized = self.windowState() & Qt.WindowState.WindowMinimized
            for child in self.findChildren(QDialog):
                if is_minimized:
                    child.showMinimized()
                else:
                    child.showNormal()
        super().changeEvent(event)


    def closeEvent(self, event: QCloseEvent):
        """Override close behavior for minimize-to-tray feature."""
        minimize_to_tray = ThemeManager.get_setting("minimize_to_tray", False)
        if minimize_to_tray:
            event.ignore()
            self.hide()
            if self.tray_icon:
                self.tray_icon.showMessage(
                    APP_NAME,
                    "Application minimized to tray.",
                    QSystemTrayIcon.MessageIcon.Information,
                    2000
                )
        else:
            event.accept()

