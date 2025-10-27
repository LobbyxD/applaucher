# ui/widgets/title_bar.py
from PyQt6.QtCore import QSize, Qt, QPoint
from PyQt6.QtGui import QIcon
from PyQt6.QtWidgets import (
    QWidget, QHBoxLayout, QLabel, QMenuBar, QPushButton, QSizePolicy
)

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
        self.btn_min.clicked.connect(self._root.showMinimized)
        self.btn_max.clicked.connect(self._toggle_maximize)
        self.btn_close.clicked.connect(self._root.close)

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
    def _toggle_maximize(self):
        if self._is_max:
            self._root.showNormal()
            self._is_max = False
            self.btn_max.setIcon(themed_icon("window_maximize.svg"))
        else:
            self._root.showMaximized()
            self._is_max = True
            self.btn_max.setIcon(themed_icon("window_restore.svg"))

