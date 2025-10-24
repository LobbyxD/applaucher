# app_launcher.py — PyQt6 rewrite (single-file)
# Requires: pip install PyQt6
# Keeps your backend: launcher_logic.run_launch_sequence

from __future__ import annotations
import sys, os, json, threading
from typing import List, Dict, Any, Optional
import asyncio
from PyQt6.QtCore import QCoreApplication, QStandardPaths
from PyQt6.QtCore import Qt, QSize, QPoint, QSettings
from PyQt6.QtGui import QAction, QIcon
from PyQt6.QtWidgets import (
    QApplication, QMainWindow, QWidget, QDialog,
    QVBoxLayout, QHBoxLayout, QGridLayout,
    QLabel, QLineEdit, QPushButton, QListWidget, QListWidgetItem,
    QDoubleSpinBox, QComboBox, QFileDialog, QMessageBox, QFrame, QCheckBox
)
import os, json
from launcher_logic import run_launch_sequence


QCoreApplication.setOrganizationName("Lobbyx3")
QCoreApplication.setApplicationName("App Launcher")

APP_NAME = "App Launcher"
DATA_FILE = "launches.json"

MODES = ["Not Maximized", "Maximized", "Minimized"]

# =========================
# Theme manager (No flicker)
# =========================

class ThemeManager:
    SETTINGS_FILE = os.path.join(
        QStandardPaths.writableLocation(QStandardPaths.StandardLocation.AppDataLocation),
        "settings.json"
    )

    @staticmethod
    def _load() -> dict:
        if os.path.exists(ThemeManager.SETTINGS_FILE):
            try:
                with open(ThemeManager.SETTINGS_FILE, "r", encoding="utf-8") as f:
                    return json.load(f)
            except Exception:
                pass
        return {}

    @staticmethod
    def is_dark() -> bool:
        data = ThemeManager._load()
        # Default to dark if not found
        return bool(data.get("dark", True))

    @staticmethod
    def set_dark(value: bool):
        os.makedirs(os.path.dirname(ThemeManager.SETTINGS_FILE), exist_ok=True)
        data = ThemeManager._load()
        data["dark"] = bool(value)
        with open(ThemeManager.SETTINGS_FILE, "w", encoding="utf-8") as f:
            json.dump(data, f, indent=2)

    def main():
        app = QApplication(sys.argv)
        # 🔧 Set org/app name so QStandardPaths knows where to store data
        QCoreApplication.setOrganizationName("Lobbyx3")
        QCoreApplication.setApplicationName("App Launcher")

        # apply saved theme
        ThemeManager.apply(app, ThemeManager.is_dark())

        w = MainWindow()
        w.show()
        sys.exit(app.exec())

    @staticmethod
    def apply(app, dark: bool):
        """Apply Qt palette + QSS styling for dark/light mode."""
        from PyQt6.QtWidgets import QStyleFactory
        from PyQt6.QtGui import QPalette, QColor

        app.setStyle(QStyleFactory.create("Fusion"))
        p = QPalette()

        def set_color(role, hex_color):
            p.setColor(getattr(QPalette.ColorRole, role), QColor(hex_color))

        if dark:
            # --- Dark palette ---
            set_color("Window", "#111827")
            set_color("WindowText", "#e5e7eb")
            set_color("Base", "#0f172a")
            set_color("AlternateBase", "#1e293b")
            set_color("Text", "#e5e7eb")
            set_color("Button", "#1e293b")
            set_color("ButtonText", "#e5e7eb")
            set_color("Highlight", "#3b82f6")
            set_color("HighlightedText", "#111827")
        else:
            # --- Light palette ---
            set_color("Window", "#f9fafb")
            set_color("WindowText", "#111827")
            set_color("Base", "#ffffff")
            set_color("AlternateBase", "#ffffff")
            set_color("Text", "#111827")
            set_color("Button", "#ffffff")
            set_color("ButtonText", "#111827")
            set_color("Highlight", "#2563eb")
            set_color("HighlightedText", "#ffffff")

        app.setPalette(p)
        app.setStyleSheet("""
        QWidget { font-size: 14px; }
        QFrame#card { border-radius: 12px; border: 1px solid palette(Midlight); }
        QLineEdit, QDoubleSpinBox, QComboBox, QListWidget {
            border-radius: 8px; padding: 6px; border: 1px solid palette(Midlight);
        }
        QPushButton { border-radius: 8px; padding: 8px 12px; }
        QPushButton:hover { opacity: 0.9; }
        """)

# =========================
# Path row widget (editor)
# =========================
class PathRow(QWidget):
    def __init__(self, path: str = "", delay: float = 0.0, mode: str = "Not Maximized"):
        super().__init__()
        self.path_edit = QLineEdit(path)
        self.path_edit.setPlaceholderText("Path to .exe / .bat / .cmd / .lnk")
        self.browse_btn = QPushButton("📁")
        self.browse_btn.setFixedWidth(36)
        self.delay = QDoubleSpinBox()
        self.delay.setRange(0, 9999)
        self.delay.setDecimals(2)
        self.delay.setSuffix(" s")
        self.delay.setValue(float(delay))
        self.mode = QComboBox()
        self.mode.addItems(MODES)
        if mode in MODES:
            self.mode.setCurrentText(mode)
        self.delete_btn = QPushButton("🗑")
        self.delete_btn.setFixedWidth(36)

        # visual handle label (drag is handled by QListWidget itself)
        self.handle = QLabel("☰")
        self.handle.setFixedWidth(20)
        self.handle.setToolTip("Drag to reorder")

        row = QHBoxLayout(self)
        row.setContentsMargins(8, 6, 8, 6)
        row.setSpacing(8)
        row.addWidget(self.handle)
        row.addWidget(self.path_edit, 1)
        row.addWidget(self.browse_btn)
        row.addWidget(QLabel("Delay:"))
        row.addWidget(self.delay)
        row.addWidget(QLabel("Mode:"))
        row.addWidget(self.mode)
        row.addWidget(self.delete_btn)

        self.browse_btn.clicked.connect(self._pick)

    def _pick(self):
        f, _ = QFileDialog.getOpenFileName(
            self, "Choose Executable", "",
            "Executables (*.exe *.bat *.cmd *.lnk);;All files (*.*)"
        )
        if f:
            self.path_edit.setText(f)

    def value(self) -> Dict[str, Any]:
        return {
            "path": self.path_edit.text().strip(),
            "delay": float(self.delay.value()),
            "start_option": self.mode.currentText(),
        }


# =========================
# Add/Edit dialog
# =========================
class LaunchEditor(QDialog):
    def __init__(self, existing: Optional[Dict[str, Any]] = None, dark: bool = True, on_save=None):
        super().__init__()
        self.setWindowTitle("Add / Edit Launch")
        self.setMinimumSize(740, 580)
        self.setModal(True)
        self.on_save = on_save

        # header
        header = QLabel("🧩  Add / Edit Launch")
        header.setStyleSheet("font-size:22px; font-weight:600; margin-bottom: 6px;")

        # card container
        card = QFrame()
        card.setObjectName("card")

        # name
        name_lbl = QLabel("App Launcher Name")
        name_lbl.setStyleSheet("font-weight:600;")
        self.name_edit = QLineEdit(existing["name"] if existing else "")
        self.name_edit.setPlaceholderText("e.g. My Game Bundle")
        helper = QLabel("Name displayed on the main launcher list.")
        helper.setStyleSheet("font-size:12px; opacity:0.75;")

        name_box = QVBoxLayout()
        name_box.addWidget(name_lbl)
        name_box.addWidget(self.name_edit)
        name_box.addWidget(helper)

        # paths section
        paths_lbl = QLabel("Paths to Launch")
        paths_lbl.setStyleSheet("font-weight:600;")

        self.listw = QListWidget()
        self.listw.setDragDropMode(QListWidget.DragDropMode.InternalMove)
        self.listw.setDefaultDropAction(Qt.DropAction.MoveAction)
        self.listw.setSelectionMode(QListWidget.SelectionMode.NoSelection)
        self.listw.setSpacing(6)

        # load existing paths
        for p in (existing["paths"] if existing else []):
            self._add_row(p.get("path",""), p.get("delay",0.0), p.get("start_option","Not Maximized"))

        add_btn = QPushButton("➕  Add Path")
        add_btn.clicked.connect(lambda: self._add_row())

        # card layout
        inner = QVBoxLayout(card)
        inner.setContentsMargins(16, 16, 16, 16)
        inner.setSpacing(10)
        inner.addLayout(name_box)
        # subtle divider
        div = QFrame(); div.setFrameShape(QFrame.Shape.HLine)
        inner.addWidget(div)
        inner.addWidget(paths_lbl)
        inner.addWidget(self.listw, 1)
        inner.addWidget(add_btn)

        # footer
        save_btn = QPushButton("💾  Save Launch")
        cancel_btn = QPushButton("Cancel")
        footer = QHBoxLayout()
        footer.addStretch(1)
        footer.addWidget(cancel_btn)
        footer.addWidget(save_btn)

        # root
        root = QVBoxLayout(self)
        root.setContentsMargins(24, 18, 24, 18)
        root.setSpacing(12)
        root.addWidget(header)
        root.addWidget(card, 1)
        root.addLayout(footer)

        cancel_btn.clicked.connect(self.reject)
        save_btn.clicked.connect(self._save)

    def _add_row(self, path="", delay=0.0, mode="Not Maximized"):
        item = QListWidgetItem(self.listw)
        w = PathRow(path, delay, mode)
        item.setSizeHint(QSize(0, 50))
        self.listw.addItem(item)
        self.listw.setItemWidget(item, w)
        w.delete_btn.clicked.connect(lambda: self._remove_item(item))

    def _remove_item(self, item: QListWidgetItem):
        row = self.listw.row(item)
        self.listw.takeItem(row)

    def _save(self):
        name = (self.name_edit.text() or "").strip() or "Untitled"
        paths = []
        for i in range(self.listw.count()):
            it = self.listw.item(i)
            w: PathRow = self.listw.itemWidget(it)
            v = w.value()
            if v["path"]:
                paths.append(v)
        if not paths:
            QMessageBox.warning(self, "Empty", "Please add at least one path.")
            return
        if self.on_save:
            self.on_save({"name": name, "paths": paths})
        self.accept()


# =========================
# Settings (theme toggle)
# =========================
class SettingsDialog(QDialog):
    def __init__(self, parent=None, dark: bool = True, on_changed=None):
        super().__init__(parent)
        self.setWindowTitle("Settings")
        self.setModal(True)
        self.setMinimumWidth(360)
        self.on_changed = on_changed

        card = QFrame(); card.setObjectName("card")
        row = QHBoxLayout(card)
        row.setContentsMargins(16, 16, 16, 16)
        row.setSpacing(12)
        label = QLabel("Dark Mode")
        self.toggle = QCheckBox()
        self.toggle.setChecked(dark)
        row.addWidget(label)
        row.addStretch(1)
        row.addWidget(self.toggle)

        btns = QHBoxLayout()
        btns.addStretch(1)
        close = QPushButton("Close")
        btns.addWidget(close)

        root = QVBoxLayout(self)
        root.setContentsMargins(24, 18, 24, 18)
        root.setSpacing(12)
        header = QLabel("⚙️  Settings"); header.setStyleSheet("font-size:20px; font-weight:600;")
        root.addWidget(header)
        root.addWidget(card)
        root.addLayout(btns)

        close.clicked.connect(self.accept)
        self.toggle.stateChanged.connect(self._apply)

    def _apply(self):
        if self.on_changed:
            self.on_changed(bool(self.toggle.isChecked()))


# =========================
# Main Window
# =========================
class MainWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle(APP_NAME)
        self.resize(880, 600)
        self.launches: List[Dict[str, Any]] = []
        self._load_data()

        central = QWidget()
        self.setCentralWidget(central)

        # header
        title = QLabel("🚀  App Launcher")
        title.setStyleSheet("font-size:22px; font-weight:700; margin-bottom:4px;")
        subtitle = QLabel("Create launch bundles with multiple paths, delays and window modes.")

        # card (list)
        card = QFrame(); card.setObjectName("card")
        card_layout = QVBoxLayout(card)
        card_layout.setContentsMargins(16, 16, 16, 16)
        card_layout.setSpacing(10)

        # list with internal drag
        self.listw = QListWidget()
        self.listw.setDragDropMode(QListWidget.DragDropMode.InternalMove)
        self.listw.setDefaultDropAction(Qt.DropAction.MoveAction)
        self.listw.setSelectionMode(QListWidget.SelectionMode.SingleSelection)
        self.listw.setSpacing(6)

        # buttons
        btn_row = QHBoxLayout()
        self.add_btn = QPushButton("➕  Add")
        self.edit_btn = QPushButton("✏️  Edit")
        self.del_btn = QPushButton("🗑  Delete")
        self.run_btn = QPushButton("▶  Run")
        btn_row.addWidget(self.add_btn)
        btn_row.addWidget(self.edit_btn)
        btn_row.addWidget(self.del_btn)
        btn_row.addStretch(1)
        btn_row.addWidget(self.run_btn)

        card_layout.addWidget(QLabel("Launchers"))
        card_layout.addWidget(self.listw, 1)
        card_layout.addLayout(btn_row)

        root = QVBoxLayout(central)
        root.setContentsMargins(24, 18, 24, 18)
        root.setSpacing(12)
        root.addWidget(title)
        root.addWidget(subtitle)
        root.addWidget(card, 1)

        # menu
        menu = self.menuBar().addMenu("App")
        act_settings = QAction("Settings…", self)
        act_quit = QAction("Quit", self)
        menu.addAction(act_settings)
        menu.addSeparator()
        menu.addAction(act_quit)

        # signals
        self.add_btn.clicked.connect(self._add)
        self.edit_btn.clicked.connect(self._edit)
        self.del_btn.clicked.connect(self._delete)
        self.run_btn.clicked.connect(self._run_selected)
        self.listw.itemDoubleClicked.connect(lambda _: self._run_selected())
        self.listw.model().rowsMoved.connect(self._rows_moved)  # update order on drag
        act_settings.triggered.connect(self._open_settings)
        act_quit.triggered.connect(self.close)

        self._refresh_list()

    # ---------- data ----------
    def _data_path(self) -> str:
        # Get user's %APPDATA%/App Launcher
        base_dir = QStandardPaths.writableLocation(QStandardPaths.StandardLocation.AppDataLocation)
        os.makedirs(base_dir, exist_ok=True)
        return os.path.join(base_dir, DATA_FILE)


    def _load_data(self):
        p = self._data_path()
        if os.path.exists(p):
            try:
                with open(p, "r", encoding="utf-8") as f:
                    self.launches = json.load(f)
            except Exception:
                self.launches = []
        else:
            self.launches = []

    def _save_data(self):
        p = self._data_path()
        try:
            with open(p, "w", encoding="utf-8") as f:
                json.dump(self.launches, f, indent=2)
        except Exception as e:
            QMessageBox.critical(self, "Error", f"Failed to save:\n{e}")

    # ---------- UI helpers ----------
    def _refresh_list(self):
        self.listw.clear()
        for bundle in self.launches:
            name = bundle.get("name", "Untitled")
            item = QListWidgetItem(name)
            item.setData(Qt.ItemDataRole.UserRole, bundle)
            self.listw.addItem(item)

    def _current_index(self) -> int:
        row = self.listw.currentRow()
        return row if row >= 0 else -1

    def _rows_moved(self, *_):
        # Update self.launches to match list order
        new_order = []
        for i in range(self.listw.count()):
            bundle = self.listw.item(i).data(Qt.ItemDataRole.UserRole)
            new_order.append(bundle)
        self.launches = new_order
        self._save_data()

    # ---------- actions ----------
    def _add(self):
        dark = ThemeManager.is_dark()
        def on_save(data):
            self.launches.append(data)
            self._save_data()
            self._refresh_list()
        dlg = LaunchEditor(existing=None, dark=dark, on_save=on_save)
        dlg.exec()

    def _edit(self):
        i = self._current_index()
        if i < 0:
            return
        dark = ThemeManager.is_dark()
        def on_save(data):
            self.launches[i] = data
            self._save_data()
            self._refresh_list()
            self.listw.setCurrentRow(i)
        existing = self.launches[i]
        dlg = LaunchEditor(existing=existing, dark=dark, on_save=on_save)
        dlg.exec()

    def _delete(self):
        i = self._current_index()
        if i < 0:
            return
        name = self.launches[i].get("name", "Untitled")
        if QMessageBox.question(self, "Delete", f"Delete '{name}'?") == QMessageBox.StandardButton.Yes:
            self.launches.pop(i)
            self._save_data()
            self._refresh_list()

    def _run_selected(self):
        i = self._current_index()
        if i < 0:
            return
        bundle = self.launches[i]

        def worker():
            try:
                asyncio.run(run_launch_sequence(bundle["paths"]))
  # <- keep your existing backend
            except Exception as e:
                # show error on UI thread
                from PyQt6.QtCore import QTimer
                QTimer.singleShot(0, lambda: QMessageBox.critical(self, "Error", str(e)))

        threading.Thread(target=worker, daemon=True).start()

    def _open_settings(self):
        dark = ThemeManager.is_dark()
        def on_changed(v: bool):
            ThemeManager.set_dark(v)
            ThemeManager.apply(QApplication.instance(), v)  # instant, no flicker
        dlg = SettingsDialog(self, dark=dark, on_changed=on_changed)
        dlg.exec()


# =========================
# Entrypoint
# =========================
def main():
    app = QApplication(sys.argv)
    QCoreApplication.setOrganizationName("Lobbyx3")
    QCoreApplication.setApplicationName("App Launcher")

    # ✅ Load icon from runtime directory (works after PyInstaller freeze)
    base_dir = getattr(sys, "_MEIPASS", os.path.dirname(os.path.abspath(__file__)))
    icon_path = os.path.join(base_dir, "AppLauncher.ico")
    app_icon = QIcon(icon_path)
    app.setWindowIcon(app_icon)

    ThemeManager.apply(app, ThemeManager.is_dark())

    w = MainWindow()
    w.setWindowIcon(app_icon)
    w.show()
    sys.exit(app.exec())



if __name__ == "__main__":
    main()
