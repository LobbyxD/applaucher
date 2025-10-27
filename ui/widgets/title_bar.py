# ui/widgets/title_bar.py
from PyQt6.QtCore import QEasingCurve, QPoint, QPropertyAnimation, QSize, Qt
from PyQt6.QtGui import QIcon
from PyQt6.QtWidgets import (QGraphicsOpacityEffect, QHBoxLayout, QLabel,
                             QMenuBar, QPushButton, QSizePolicy, QWidget)

from ui.icon_loader import themed_icon
from ui.theme_manager import ThemeManager
from ui.widgets.style_helpers import apply_titlebar_style


class TitleBar(QWidget):
    """VS Code–style title bar with icon, menu, and window buttons."""
    def __init__(self, parent, menu_bar=None, app_icon_path=None):
        super().__init__(parent)
        self._root = parent
        self._drag_pos = None
        self._is_max = False
        self.setObjectName("AppTitleBar")
        self.setFixedHeight(34)

        layout = QHBoxLayout(self)
        layout.setContentsMargins(8, 0, 6, 0)
        layout.setSpacing(6)

        # === Left: App icon ===
        icon_lbl = QLabel()
        if app_icon_path:
            icon_lbl.setPixmap(QIcon(app_icon_path).pixmap(18, 18))
        icon_lbl.setFixedSize(QSize(20, 20))

        # === Middle: Menu bar ===
        self.menu_bar = menu_bar or QMenuBar(self)
        self.menu_bar.setNativeMenuBar(False)
        self.menu_bar.setSizePolicy(QSizePolicy.Policy.Minimum, QSizePolicy.Policy.Preferred)
        self.menu_bar.setObjectName("EmbeddedMenuBar")

        # === Right: Window buttons ===
        self.btn_min = QPushButton()
        self.btn_max = QPushButton()
        self.btn_close = QPushButton()

        # Use theme-aware icons
        self.btn_min.setIcon(themed_icon("window_minimize.svg"))
        self.btn_max.setIcon(themed_icon("window_maximize.svg"))
        self.btn_close.setIcon(themed_icon("delete.svg"))

        for btn in (self.btn_min, self.btn_max, self.btn_close):
            btn.setIconSize(QSize(14, 14))
            btn.setFlat(True)
            btn.setFocusPolicy(Qt.FocusPolicy.NoFocus)
            btn.setFixedSize(38, 26)

        # Compose layout
        # Left group: icon + menus sized to content
        left_group = QWidget()
        left_lay = QHBoxLayout(left_group)
        left_lay.setContentsMargins(0, 0, 0, 0)
        left_lay.setSpacing(4)
        left_lay.addWidget(icon_lbl, 0, Qt.AlignmentFlag.AlignVCenter)
        left_lay.addWidget(self.menu_bar, 0, Qt.AlignmentFlag.AlignVCenter)

        # Middle: wide drag area that soaks up all remaining space
        drag_area = QWidget()
        drag_area.setObjectName("DragArea")
        drag_area.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Preferred)
        drag_area.setMinimumHeight(self.height())  # match bar height

        # Right: window buttons
        right_group = QWidget()
        right_lay = QHBoxLayout(right_group)
        right_lay.setContentsMargins(0, 0, 0, 0)
        right_lay.setSpacing(0)
        right_lay.addWidget(self.btn_min, 0)
        right_lay.addWidget(self.btn_max, 0)
        right_lay.addWidget(self.btn_close, 0)

        # Assemble the title row
        layout.addWidget(left_group, 0)
        layout.addWidget(drag_area, 1)     # ← big, comfy drag zone
        layout.addWidget(right_group, 0)
        self._wire_drag_area(drag_area)


        # Actions
        self.btn_min.clicked.connect(self._animate_minimize)
        self.btn_max.clicked.connect(self._toggle_maximize)
        self.btn_close.clicked.connect(self._animate_close)

        # Apply style
        apply_titlebar_style(self)
        ThemeManager.instance().theme_changed.connect(lambda _: apply_titlebar_style(self))

    # --- Drag area behavior (only the empty spacer drags) ---
    def _wire_drag_area(self, widget):
        def _press(e):
            if e.button() == Qt.MouseButton.LeftButton:
                self._drag_pos = e.globalPosition().toPoint()
        def _move(e):
            if self._drag_pos and e.buttons() == Qt.MouseButton.LeftButton:
                delta = e.globalPosition().toPoint() - self._drag_pos
                self._root.move(self._root.pos() + delta)
                self._drag_pos = e.globalPosition().toPoint()
        def _release(e):
            self._drag_pos = None

        widget.mousePressEvent = _press
        widget.mouseMoveEvent = _move
        widget.mouseReleaseEvent = _release

    # --- Behavior ---
    # --- True Windows maximize / restore animation for frameless window ---
    def _toggle_maximize(self):
        """Trigger Windows-native maximize/restore animations with full state sync."""
        try:
            import ctypes
            from ctypes import wintypes

            user32 = ctypes.windll.user32
            GWL_STYLE = -16
            WS_CAPTION = 0x00C00000
            WS_THICKFRAME = 0x00040000
            WS_MAXIMIZE = 0x01000000
            WM_SYSCOMMAND = 0x0112
            SC_MAXIMIZE = 0xF030
            SC_RESTORE = 0xF120

            hwnd = int(self._root.winId())

            # Read current window style to determine real state
            style = user32.GetWindowLongW(hwnd, GWL_STYLE)
            is_really_maximized = bool(style & WS_MAXIMIZE)

            # Temporarily restore WS_CAPTION + WS_THICKFRAME so DWM animates
            user32.SetWindowLongW(hwnd, GWL_STYLE, style | WS_CAPTION | WS_THICKFRAME)

            if not is_really_maximized:
                # --- Maximize with native animation ---
                user32.PostMessageW(hwnd, WM_SYSCOMMAND, SC_MAXIMIZE, 0)
                self._is_max = True
                self.btn_max.setIcon(themed_icon("window_restore.svg"))
            else:
                # --- Restore (normalize) with native animation ---
                user32.PostMessageW(hwnd, WM_SYSCOMMAND, SC_RESTORE, 0)
                self._is_max = False
                self.btn_max.setIcon(themed_icon("window_maximize.svg"))

            # Once the state changes, remove native borders again
            def _restore_styles():
                # Check current style again after transition
                s = user32.GetWindowLongW(hwnd, GWL_STYLE)
                # Only remove caption + frame if not minimized or maximized
                if not (s & WS_MAXIMIZE):
                    user32.SetWindowLongW(hwnd, GWL_STYLE, s & ~WS_CAPTION & ~WS_THICKFRAME)

            # Avoid stacking connections — disconnect existing first
            try:
                self._root.windowStateChanged.disconnect()
            except Exception:
                pass
            self._root.windowStateChanged.connect(lambda _: _restore_styles())

        except Exception:
            # fallback to normal Qt behavior on non-Windows
            if self._is_max:
                self._root.showNormal()
                self._is_max = False
                self.btn_max.setIcon(themed_icon("window_restore.svg"))
            else:
                self._root.showMaximized()
                self._is_max = True
                self.btn_max.setIcon(themed_icon("window_maximize.svg"))

    # --- True Windows minimize animation for frameless window ---
    def _animate_minimize(self):
        """Temporarily restore WS_CAPTION so Windows plays its native animation."""
        try:
            import ctypes
            from ctypes import wintypes

            user32 = ctypes.windll.user32
            GWL_STYLE = -16
            WS_CAPTION = 0x00C00000
            WS_THICKFRAME = 0x00040000
            WM_SYSCOMMAND = 0x0112
            SC_MINIMIZE = 0xF020

            hwnd = int(self._root.winId())

            # 1️⃣  Add normal window styles so DWM can animate
            style = user32.GetWindowLongW(hwnd, GWL_STYLE)
            user32.SetWindowLongW(hwnd, GWL_STYLE, style | WS_CAPTION | WS_THICKFRAME)

            # 2️⃣  Ask Windows to minimize (this triggers the system animation)
            user32.PostMessageW(hwnd, WM_SYSCOMMAND, SC_MINIMIZE, 0)

            # 3️⃣  After minimize, remove those bits again when restored
            #     (otherwise the native border will reappear)
            def _restore_styles():
                if not self._root.isMinimized():
                    # remove the caption again once restored
                    s = user32.GetWindowLongW(hwnd, GWL_STYLE)
                    user32.SetWindowLongW(hwnd, GWL_STYLE, s & ~WS_CAPTION & ~WS_THICKFRAME)

            self._root.windowStateChanged.connect(lambda _: _restore_styles())

        except Exception:
            # fallback on non-Windows systems
            self._root.showMinimized()

    def showEvent(self, e):
        """Fade in on restore."""
        if hasattr(self._root, "_fade_effect"):
            effect = self._root._fade_effect
            effect.setOpacity(0.0)
            anim = QPropertyAnimation(effect, b"opacity", self)
            anim.setDuration(150)
            anim.setStartValue(0.0)
            anim.setEndValue(1.0)
            anim.setEasingCurve(QEasingCurve.Type.InOutQuad)
            anim.start(QPropertyAnimation.DeletionPolicy.DeleteWhenStopped)
        super().showEvent(e)

    def mouseDoubleClickEvent(self, e):
        """Double-click title bar toggles maximize/restore."""
        if e.button() == Qt.MouseButton.LeftButton:
            self._toggle_maximize()

    # --- True Windows close animation for frameless window ---
    def _animate_close(self):
        """Trigger Windows-native close animation using SC_CLOSE."""
        try:
            import ctypes
            from ctypes import wintypes

            user32 = ctypes.windll.user32
            GWL_STYLE = -16
            WS_CAPTION = 0x00C00000
            WS_THICKFRAME = 0x00040000
            WM_SYSCOMMAND = 0x0112
            SC_CLOSE = 0xF060

            hwnd = int(self._root.winId())

            # Restore normal window style so DWM owns it for animation
            style = user32.GetWindowLongW(hwnd, GWL_STYLE)
            user32.SetWindowLongW(hwnd, GWL_STYLE, style | WS_CAPTION | WS_THICKFRAME)

            # Ask Windows to perform the native close animation
            user32.PostMessageW(hwnd, WM_SYSCOMMAND, SC_CLOSE, 0)

        except Exception:
            # Fallback on non-Windows
            self._root.close()
