# ui/main_window/actions.py
import json
import os
import sys
import uuid
import tempfile
import shutil
import pythoncom
from PyQt6.QtCore import QStandardPaths, Qt, QThread
from PyQt6.QtWidgets import QApplication, QFileDialog, QMessageBox, QDialog
from win32com.client import Dispatch

from core.app_settings import APP_SETTINGS
from core.storage import load_launches, save_launches
from ui.dialogs.launch_editor import LaunchEditor
from ui.dialogs.settings_dialog import SettingsDialog
from ui.icon_loader import themed_icon
from ui.main_window.launch_worker import LaunchWorker
from core.utils import sanitize_filename
from ui.theme_manager import ThemeManager

APP_NAME = APP_SETTINGS["window_title"]

def _icon_store_dir() -> str:
    base = os.path.join(os.getenv("APPDATA", ""), "App Launcher", "Icons")
    os.makedirs(base, exist_ok=True)
    return base


def _ensure_ico(source_path: str, out_name_hint: str) -> str:
    if source_path.lower().endswith(".ico"):
        return source_path

    from PIL import Image

    out_dir = _icon_store_dir()

    unique_name = f"{out_name_hint}_{uuid.uuid4().hex}.ico"
    out_path = os.path.join(out_dir, unique_name)

    img = Image.open(source_path).convert("RGBA")
    img.save(
        out_path,
        format="ICO",
        sizes=[(256, 256), (128, 128), (64, 64), (48, 48), (32, 32), (16, 16)],
    )

    return out_path


class Actions:
    def __init__(self, window):
        self.window = window
        self._delete_pending = None

    # -------------------- MENU --------------------
    def build_menu(self, menubar):
        app_menu = menubar.addMenu("File")
        self.act_import = app_menu.addAction("Import Launchers…")
        self.act_export = app_menu.addAction("Export Launchers…")
        app_menu.addSeparator()
        act_settings = app_menu.addAction("Settings…")
        app_menu.addSeparator()
        act_quit = app_menu.addAction("Quit")

        self.act_import.setIcon(themed_icon("import.svg"))
        self.act_export.setIcon(themed_icon("export.svg"))
        self.act_import.triggered.connect(self._import_launchers)
        self.act_export.triggered.connect(self._export_launchers)
        act_settings.triggered.connect(self._open_settings)
        act_quit.triggered.connect(QApplication.instance().quit)

    def refresh_icons(self):
        """Safely refresh menu action icons (theme-aware)."""
        if hasattr(self, "act_import"):
            self.act_import.setIcon(themed_icon("import.svg"))
        if hasattr(self, "act_export"):
            self.act_export.setIcon(themed_icon("export.svg"))


    # -------------------- CRUD --------------------
    def add_launcher(self):
        def on_save(data):
            self.window.launches.append(data)
            save_launches(self.window.launches)
            self.window._refresh_list()
        LaunchEditor(on_save=on_save, parent=self.window).exec()

    def edit_launcher(self, i):
        def on_save(data):
            self.window.launches[i] = data
            save_launches(self.window.launches)
            self.window._refresh_list()
        LaunchEditor(existing=self.window.launches[i], on_save=on_save, parent=self.window).exec()

    def delete_launcher(self, i):
        if self._delete_pending == i:
            name = self.window.launches[i].get("name", "Untitled")
            self.window.launches.pop(i)
            save_launches(self.window.launches)
            self.window._refresh_list()
            self._delete_pending = None
        else:
            self._delete_pending = i
            self.window._show_message("⚠️ Click delete again to confirm.")

    def export_shortcut(self, i):
        import os
        import sys
        import pythoncom
        from PyQt6.QtCore import QStandardPaths
        from win32com.shell import shell  # pywin32
        from win32com.shell import shellcon

        def _make_lnk(lnk_path: str, target: str, args: str, workdir: str, icon_path: str | None):
            """
            Create a .lnk using IShellLinkW + IPersistFile (Unicode-safe).
            Does NOT use WScript.Shell.
            """
            # Create ShellLink COM object
            sl = pythoncom.CoCreateInstance(
                shell.CLSID_ShellLink,
                None,
                pythoncom.CLSCTX_INPROC_SERVER,
                shell.IID_IShellLink,
            )

            sl.SetPath(target)
            sl.SetArguments(args)
            sl.SetWorkingDirectory(workdir)

            if icon_path and os.path.exists(icon_path):
                sl.SetIconLocation(icon_path, 0)

            # Save via IPersistFile (this is the key for Unicode-safe save)
            pf = sl.QueryInterface(pythoncom.IID_IPersistFile)

            # IPersistFile.Save expects a Unicode string path
            pf.Save(lnk_path, 0)

        try:
            bundle = self.window.launches[i]
            name = bundle.get("name", "Untitled").strip() or "Untitled"
            safe = sanitize_filename(name)  # if your sanitize removes Hebrew, consider allowing it

            # Resolve Desktop (handles OneDrive redirected desktop correctly)
            desktop = QStandardPaths.writableLocation(QStandardPaths.StandardLocation.DesktopLocation)
            if not desktop or not os.path.exists(desktop):
                desktop = os.path.join(os.path.expanduser("~"), "Desktop")

            final_path = os.path.abspath(os.path.join(desktop, f"{safe}.lnk"))

            # ---- resolve target/args/workdir/icon ----
            # ---- icon selection flow ----
            # If frozen: default icon should be the EXE icon → do NOT set IconLocation at all (None).
            # If not frozen (dev): pythonw.exe icon is wrong → we set AppLauncher.ico as default.
            default_dev_icon = os.path.abspath(
                os.path.join(os.path.dirname(__file__), "..", "..", "resources", "icons", "AppLauncher.ico")
            )

            # Ask user if they want custom icon
            reply = QMessageBox.question(
                self.window,
                "Shortcut Icon",
                "Would you like to choose a custom icon for this shortcut?",
                QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
                QMessageBox.StandardButton.No,
            )

            use_custom_icon = (reply == QMessageBox.StandardButton.Yes)

            icon_path_for_shortcut: str | None

            if use_custom_icon:
                picked, _ = QFileDialog.getOpenFileName(
                    self.window,
                    "Choose Icon Image",
                    "",
                    "Icon / Images (*.ico *.png *.jpg *.jpeg);;All Files (*.*)",
                )
                if not picked:
                    return  # user canceled → no shortcut created

                safe_hint = sanitize_filename(name) or uuid.uuid4().hex
                try:
                    icon_path_for_shortcut = _ensure_ico(picked, safe_hint)
                except Exception as e:
                    QMessageBox.critical(self.window, "Icon Error", str(e))
                    return

            else:
                # No custom icon:
                # - Frozen → None (uses the target EXE's embedded icon)
                # - Dev → use AppLauncher.ico so shortcut looks like the app
                icon_path_for_shortcut = None if getattr(sys, "frozen", False) else default_dev_icon

            if getattr(sys, "frozen", False):
                pyexe = sys.executable
                if pyexe.lower().endswith("python.exe"):
                    pyexe = pyexe.replace("python.exe", "pythonw.exe")

                target = pyexe
                args = f'--launch "{name}"'
                workdir = os.path.dirname(sys.executable)

                icon_path = os.path.join(workdir, "resources", "icons", "AppLauncher.ico")
                if not os.path.exists(icon_path) and hasattr(sys, "_MEIPASS"):
                    icon_path = os.path.join(sys._MEIPASS, "resources", "icons", "AppLauncher.ico")
            else:
                pyexe = sys.executable
                if pyexe.lower().endswith("python.exe"):
                    pyexe = pyexe.replace("python.exe", "pythonw.exe")

                target = pyexe
                main_py = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..", "main.py"))
                args = f'"{main_py}" --launch "{name}"'
                workdir = os.path.dirname(main_py)

                icon_path = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..", "resources", "icons", "AppLauncher.ico"))

            # Ensure no existing broken link blocks save
            if os.path.exists(final_path):
                os.remove(final_path)

            pythoncom.CoInitialize()
            try:
                _make_lnk(final_path, target, args, workdir, icon_path_for_shortcut)
            finally:
                pythoncom.CoUninitialize()

            self.window._show_message(f"Desktop shortcut created: {safe}")

        except Exception as e:
            self.window._show_message(f"❌ Export failed: {e}")


    # -------------------- RUN --------------------
    def run_launcher(self, i):
        """Run the selected launcher asynchronously with live status updates."""
        bundle = self.window.launches[i]
        name = bundle.get("name", "Untitled")

        # --- Create worker + thread ---
        thread = QThread(self.window)
        worker = LaunchWorker(bundle["paths"], name)
        worker.moveToThread(thread)

        # --- Connect signals ---
        thread.started.connect(worker.run)
        worker.progress.connect(self.window._show_message)
        worker.finished.connect(lambda msg: self.window._show_message(msg, 3000))

        # --- Clean up thread safely ---
        worker.finished.connect(thread.quit)
        thread.finished.connect(worker.deleteLater)
        thread.finished.connect(thread.deleteLater)

        # --- Keep strong refs to prevent GC ---
        self._launch_thread = thread
        self._launch_worker = worker

        # --- Start thread ---
        thread.start()


    # -------------------- SETTINGS --------------------
    def _open_settings(self):
        def on_changed(v: bool):
            ThemeManager.set_dark(v)
            app = QApplication.instance()
            ThemeManager.apply(app, v)
        SettingsDialog(self.window, dark=ThemeManager.is_dark(), on_changed=on_changed).exec()

    # -------------------- IMPORT/EXPORT --------------------
    def _export_launchers(self):
        downloads = QStandardPaths.writableLocation(QStandardPaths.StandardLocation.DownloadLocation)
        if not downloads or not os.path.exists(downloads):
            downloads = os.path.expanduser("~/Downloads")
        file, _ = QFileDialog.getSaveFileName(
            self.window, "Export Launchers", os.path.join(downloads, "launches_export.json"), "JSON Files (*.json)"
        )
        if not file: return
        try:
            with open(file, "w", encoding="utf-8") as f:
                json.dump(self.window.launches, f, indent=2)
            self.window._show_message(f"✅ Exported: {os.path.basename(file)}")
        except Exception as e:
            self.window._show_message(f"❌ Export failed: {e}")

    def _import_launchers(self):
        file, _ = QFileDialog.getOpenFileName(self.window, "Import Launchers", "", "JSON Files (*.json)")
        if not file: return
        try:
            with open(file, "r", encoding="utf-8") as f:
                imported = json.load(f)
        except Exception as e:
            QMessageBox.critical(self.window, "Invalid File", str(e))
            return
        if not isinstance(imported, list):
            QMessageBox.critical(self.window, "Invalid Format", "JSON root must be a list.")
            return
        msg = QMessageBox(self.window)
        msg.setWindowTitle("Import Launchers")
        msg.setText("Merge or replace existing launchers?")
        merge = msg.addButton("Merge", QMessageBox.ButtonRole.YesRole)
        replace = msg.addButton("Replace", QMessageBox.ButtonRole.NoRole)
        cancel = msg.addButton("Cancel", QMessageBox.ButtonRole.RejectRole)
        msg.exec()
        if msg.clickedButton() == cancel: return
        elif msg.clickedButton() == merge:
            existing = {x.get("name") for x in self.window.launches}
            self.window.launches += [x for x in imported if x.get("name") not in existing]
        else:
            self.window.launches = imported
        save_launches(self.window.launches)
        self.window._refresh_list()
        self.window._show_message("✅ Import complete.")

    # -------------------- MISC --------------------
    def propagate_change_event(self, event):
        """Sync minimize/restore (not maximize) with child dialogs."""
        from PyQt6.QtCore import QEvent
        if event.type() != QEvent.Type.WindowStateChange:
            return

        state = self.window.windowState()
        minimized = bool(state & Qt.WindowState.WindowMinimized)

        # Only apply when actually minimized or restored from minimized
        for dlg in self.window.findChildren(QDialog):
            if minimized:
                dlg.showMinimized()
            elif event.oldState() & Qt.WindowState.WindowMinimized:
                dlg.showNormal()
