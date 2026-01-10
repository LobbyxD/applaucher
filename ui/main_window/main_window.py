# ui/main_window/main_window.py
from PyQt6.QtCore import QSize, Qt, QTimer
from PyQt6.QtGui import QCursor
from PyQt6.QtWidgets import (QFrame, QHBoxLayout, QLabel, QListWidget,
                             QListWidgetItem, QMainWindow, QMenuBar,
                             QPushButton, QVBoxLayout, QWidget)

from core.app_settings import APP_SETTINGS
from core.storage import load_launches
from ui.icon_loader import themed_icon
from ui.main_window.actions import Actions
from ui.main_window.tray_manager import TrayManager
from ui.theme_manager import ThemeManager
from ui.widgets.style_helpers import (apply_frame_style, apply_label_style,
                                      apply_list_style, themed_label)
from ui.widgets.title_bar import TitleBar

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
        # --- Make window frameless, we draw our own title bar
        self.setWindowFlag(Qt.WindowType.FramelessWindowHint, True)
        self.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground, False) 
        self.setStatusBar(self.statusBar())
        

        # Keep a central container and stack title bar + your content
        central = QWidget(self)
        vbox = QVBoxLayout(central)
        vbox.setContentsMargins(0, 0, 0, 0)
        vbox.setSpacing(0)

        # 🔹 Set it as central before continuing (so self.centralWidget() works later)
        self.setCentralWidget(central)

        # Re-create/obtain a menu bar for embedding
        _native_mb = self.menuBar()             
        _native_mb.setVisible(False)            
        embedded_mb = QMenuBar(self)           

        # --- MOVE EXISTING MENUS into the embedded bar
        for a in list(_native_mb.actions()):
            if a.menu():
                embedded_mb.addMenu(a.menu())
            else:
                embedded_mb.addAction(a)

        # --- Title bar widget
        app_icon_path = "resources/icons/AppLauncher.ico"
        app_title = APP_SETTINGS.get("app_name", "App Launcher")
        self._title_bar = TitleBar(
                                    self,
                                    menu_bar=embedded_mb,
                                    app_icon_path=app_icon_path,
                                    )

        vbox.addWidget(self._title_bar)
        self.embedded_menu_bar = embedded_mb

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
        self.action_mgr.build_menu(self.embedded_menu_bar)

        # --- Connect signals ---
        ThemeManager.instance().theme_changed.connect(self.refresh_theme)
        self._update_win11_border_theme(ThemeManager.is_dark())

        # --- Enable Windows 11 border, corner radius, and shadow ---
        try:
            import ctypes
            from ctypes import wintypes

            dwmapi = ctypes.windll.dwmapi

            hwnd = int(self.winId())

            # 1) Let DWM render window non-client (enables shadow)
            DWMWA_NCRENDERING_POLICY = 2
            DWMNCRP_ENABLED = 2
            dwmapi.DwmSetWindowAttribute(
                wintypes.HWND(hwnd),
                wintypes.DWORD(DWMWA_NCRENDERING_POLICY),
                ctypes.byref(wintypes.DWORD(DWMNCRP_ENABLED)),
                ctypes.sizeof(wintypes.DWORD),
            )

            # 2) Rounded corners like Win11
            DWMWA_WINDOW_CORNER_PREFERENCE = 33
            DWMWCP_ROUND = 2
            dwmapi.DwmSetWindowAttribute(
                wintypes.HWND(hwnd),
                wintypes.DWORD(DWMWA_WINDOW_CORNER_PREFERENCE),
                ctypes.byref(wintypes.DWORD(DWMWCP_ROUND)),
                ctypes.sizeof(wintypes.DWORD),
            )

            # 3) Border color mode (dark/light) in sync with ThemeManager
            DWMWA_USE_IMMERSIVE_DARK_MODE = 20
            dark = ThemeManager.is_dark()
            dwmapi.DwmSetWindowAttribute(
                wintypes.HWND(hwnd),
                wintypes.DWORD(DWMWA_USE_IMMERSIVE_DARK_MODE),
                ctypes.byref(wintypes.BOOL(dark)),
                ctypes.sizeof(wintypes.BOOL),
            )

            # ❌ No DwmExtendFrameIntoClientArea here — avoids “dark spots” on opaque windows

        except Exception as e:
            print(f"⚠️ DWM border effects not applied: {e}")

    def _show_message(self, text: str, timeout: int | None = None):
        """
        Show a transient status message.
        timeout: milliseconds, or None to keep.
        """
        if hasattr(self, "statusBar"):
            if timeout:
                self.statusBar().showMessage(text, timeout)
            else:
                self.statusBar().showMessage(text)
        else:
            # fallback (should never happen)
            print(text)



    # -----------------------------
    # UI SETUP
    # -----------------------------
    def _build_ui(self):
        """Builds the main content area (below the custom title bar)."""
        # Create your main content widget
        self.main_content = QWidget()
        root = QVBoxLayout(self.main_content)
        root.setContentsMargins(16, 12, 16, 16)

        # Header
        header = QHBoxLayout()
        title = themed_label("Launcher List", bold=True, size=24)
        ThemeManager.instance().theme_changed.connect(
            lambda is_dark: apply_label_style(title, bold=True, size=24)
        )
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
        self.list_container = list_container 
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

        # ⬇️ Add the content widget (below TitleBar) into the existing vertical layout
        self.centralWidget().layout().addWidget(self.main_content)

    # -----------------------------
    # THEME + STATUS
    # -----------------------------

    def refresh_theme(self, is_dark: bool):
        """Apply app theme assets and sync Windows 11 border style."""
        # refresh icons
        self.add_btn.setIcon(themed_icon("add.svg"))
        self.action_mgr.refresh_icons()
        for i in range(self.listw.count()):
            row = self.listw.itemWidget(self.listw.item(i))
            row.refresh_icons()

            # re-style theme-aware widgets
        apply_frame_style(self.list_container, "launcherListContainer") 
        apply_list_style(self.listw)                                    

        # ✅ Sync Win11 border / dark-mode flag every time theme changes
        self._update_win11_border_theme(is_dark)

    def _update_win11_border_theme(self, is_dark: bool):
        """Tell DWM which border mode and color to use (Win11)."""
        try:
            import ctypes
            from ctypes import wintypes
            dwmapi = ctypes.windll.dwmapi
            hwnd = int(self.winId())

            # Attributes
            DWMWA_USE_IMMERSIVE_DARK_MODE = 20
            DWMWA_BORDER_COLOR = 34  # Win11 22H2+

            # 1) Flip DWM's dark mode flag
            dwmapi.DwmSetWindowAttribute(
                wintypes.HWND(hwnd),
                wintypes.DWORD(DWMWA_USE_IMMERSIVE_DARK_MODE),
                ctypes.byref(wintypes.BOOL(is_dark)),
                ctypes.sizeof(wintypes.BOOL),
            )

            # 2) Set a concrete border color from ThemeManager (prevents wrong halo)
            colors = ThemeManager.load_themes()["dark" if is_dark else "light"]
            # Expecting hex like "#RRGGBB"
            hexcol = colors.get("Border", "#404040").lstrip("#")
            r = int(hexcol[0:2], 16)
            g = int(hexcol[2:4], 16)
            b = int(hexcol[4:6], 16)

            # COLORREF is 0x00BBGGRR
            colorref = (b << 16) | (g << 8) | r
            dwmapi.DwmSetWindowAttribute(
                wintypes.HWND(hwnd),
                wintypes.DWORD(DWMWA_BORDER_COLOR),
                ctypes.byref(wintypes.DWORD(colorref)),
                ctypes.sizeof(wintypes.DWORD),
            )

        except Exception:
            # Silently ignore when not on Win11 22H2+ or if DWM isn't available
            pass

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
