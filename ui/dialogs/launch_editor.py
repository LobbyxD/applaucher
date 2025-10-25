import os
from typing import Any, Dict, Optional, cast

from PyQt6.QtCore import (QEasingCurve, QPoint, QPropertyAnimation, QSize, Qt,
                          QTimer)
from PyQt6.QtGui import QColor, QDrag, QPixmap
from PyQt6.QtWidgets import (QDialog, QFrame, QGraphicsColorizeEffect,
                             QHBoxLayout, QLabel, QLineEdit, QListWidget,
                             QListWidgetItem, QPushButton, QToolButton,
                             QVBoxLayout)

from ui.icon_loader import themed_icon
from ui.theme_manager import ThemeManager
from ui.widgets.draggable_list import DraggableList
from ui.widgets.path_row import PathRow

MODES = ["Not Maximized", "Maximized", "Minimized"]

if ThemeManager.is_dark():
    border, base, text = "#3a3a3a", "#2a2a2a", "#e6e6e6"
else:
    border, base, text = "#d0d0d0", "#ffffff", "#222222"

class LaunchEditor(QDialog):
    def __init__(self, existing: Optional[Dict[str, Any]] = None, dark: bool = True, on_save=None):
        super().__init__()
        if existing:
            name = existing.get("name", "Launcher")
            self.setWindowTitle(f"Edit {name}")
        else:
            self.setWindowTitle("Create Launcher")
        self.setMinimumSize(740, 580)
        self.setModal(True)
        self.on_save = on_save
        self.default_name_style = f"""
            QLineEdit {{
                border: 1px solid {border};
                border-radius: 6px;
                background: {base};
                color: {text};
                padding: 6px 8px;
                padding-right: 26px; 
            }}
        """

        card = QFrame()
        card.setObjectName("card")

        # --- Name field ---
        name_lbl = QLabel("Launcher Name")

        # --- Container for QLineEdit and icon (overlay style) ---
        name_container = QFrame()
        name_container.setStyleSheet("border: none;")
        name_layout = QHBoxLayout(name_container)
        name_layout.setContentsMargins(0, 0, 0, 0)
        name_layout.setSpacing(0)

        # QLineEdit styled normally
        self.name_edit = QLineEdit(existing["name"] if existing else "")
        self.name_edit.setPlaceholderText("Enter launcher name...")
        self.name_edit.setStyleSheet(self.default_name_style)
        self.name_edit.setMinimumHeight(32)
        name_layout.addWidget(self.name_edit)

       # --- Trailing info icon (theme-aware via themed_icon) ---
        self._name_trailing_action = self.name_edit.addAction(
            themed_icon("info-solid-full.svg"),
            QLineEdit.ActionPosition.TrailingPosition,
        )
        self._name_trailing_action.setToolTip("Name displayed on the main launcher list.")
        self._name_trailing_action.setEnabled(False)

        # Update the inline icon if theme changes while dialog is open
        # (Optional) Future-proof placeholder if dynamic theme reload is added.
        # Currently no signal system exists in ThemeManager, so no need to connect.


        # Combine label + field into horizontal layout
        name_box = QHBoxLayout()
        name_box.setContentsMargins(0, 0, 0, 0)
        name_box.setSpacing(8)
        name_box.addWidget(name_lbl)
        name_box.addWidget(name_container, 1)

        # --- Paths list ---
        paths_lbl = QLabel("Paths to Launch")
        self.listw = DraggableList()
        self.listw.setSelectionMode(QListWidget.SelectionMode.SingleSelection)
        self.listw.setDragEnabled(False)
        self.listw.setAcceptDrops(False)
        self.listw.setDropIndicatorShown(False)

        # Theme-based selection color
        if ThemeManager.is_dark():
            selected_bg = "#333333"   # slightly lighter than base
            hover_bg = "#2f2f2f"
            border_c = "#555555"
        else:
            selected_bg = "#eaeaea"   # slightly darker than base
            hover_bg = "#f3f3f3"
            border_c = "#c0c0c0"

        # ✅ Important: apply style only to items, not to the list widget itself
        # (so it doesn't break drag/drop rendering)
        self.listw.setStyleSheet(f"""
            QListWidget::item {{
                background: {base};
                border: 1px solid transparent;
                margin: 2px;
                padding: 4px;
            }}
            QListWidget::item:selected {{
                background: {selected_bg};
                border: 1px solid {border_c};
            }}
        """)


        # preload rows if editing
        for p in (existing["paths"] if existing else []):
            self._add_row(p.get("path", ""), p.get("delay", 0.0), p.get("start_option", "Not Maximized"))

        add_btn = QPushButton()
        add_btn.setIcon(themed_icon("add.svg"))
        add_btn.setToolTip("Add new path")
        add_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        add_btn.setFixedSize(36, 36)
        add_btn.setStyleSheet("border:none; border-radius:6px; padding:4px;")
        add_btn.clicked.connect(lambda: self._add_row())


        inner = QVBoxLayout(card)
        inner.setContentsMargins(16, 16, 16, 16)
        inner.setSpacing(10)
        inner.addLayout(name_box)

        # Divider
        divider = QFrame()
        divider.setFrameShape(QFrame.Shape.HLine)
        divider.setFrameShadow(QFrame.Shadow.Sunken)
        inner.addWidget(divider)

        inner.addWidget(paths_lbl)
        inner.addWidget(self.listw, 1)
        inner.addWidget(add_btn)

        # --- Footer ---
        save_btn = QPushButton("💾  Save Launch")
        cancel_btn = QPushButton("Cancel")
        footer = QHBoxLayout()
        footer.addStretch(1)
        footer.addWidget(cancel_btn)
        footer.addWidget(save_btn)

        # --- Inline message label ---
        self.msg_label = QLabel("")
        self.msg_label.setStyleSheet("font-size:12px; color:#f39c12;")

        # --- Root layout ---
        root = QVBoxLayout(self)
        root.setContentsMargins(24, 18, 24, 18)
        root.setSpacing(12)
        root.addWidget(card, 1)
        root.addWidget(self.msg_label)  
        root.addLayout(footer)

        cancel_btn.clicked.connect(self.reject)
        save_btn.clicked.connect(self._save)

    def _flash_name_border(self, duration: int = 3000):
        """Flash the name input field red (uses same logic as other widgets)."""
        self._flash_widget(self.name_edit, duration=duration)

   
    def _flash_widget(self, widget: QLineEdit, color: str = "#e74c3c", duration: int = 3000):
        """Flash only the given QLineEdit red, then fade out — isolated per widget."""
        if widget is None:
            return

        # Ensure previous effect is cleared cleanly
        existing = widget.graphicsEffect()
        if existing:
            existing.setEnabled(False)
            widget.setGraphicsEffect(None)

        effect = QGraphicsColorizeEffect(widget)
        effect.setColor(QColor(color))
        effect.setEnabled(True)
        effect.setStrength(1.0)
        widget.setGraphicsEffect(effect)

        # Animate strength 1.0 -> 0.0
        anim = QPropertyAnimation(effect, b"strength", self)
        anim.setDuration(duration)
        anim.setStartValue(1.0)
        anim.setEndValue(0.0)
        anim.setEasingCurve(QEasingCurve.Type.OutCubic)

        # keep a reference on the widget so GC won't kill the anim early
        if not hasattr(widget, "_flash_anims"):
            widget._flash_anims = []
        widget._flash_anims.append(anim)

        def cleanup():
            try:
                widget.setGraphicsEffect(None)
                widget._flash_anims.remove(anim)
            except Exception:
                pass

        anim.finished.connect(cleanup)
        anim.start()
    
    def _animate_reorder(self, start_row: int, end_row: int):
        """Visually animate the list item sliding to new position."""
        import math

        from PyQt6.QtCore import QPropertyAnimation, QRect

        lw = self.listw
        direction = 1 if end_row > start_row else -1
        steps = abs(end_row - start_row)

        start_rect = lw.visualItemRect(lw.item(start_row))
        end_rect = lw.visualItemRect(lw.item(end_row))
        if start_rect.isNull() or end_rect.isNull():
            return

        anim = QPropertyAnimation(lw.viewport(), b"pos")
        anim.setDuration(100 + 50 * steps)
        anim.setStartValue(start_rect.topLeft())
        anim.setEndValue(end_rect.topLeft())
        anim.setEasingCurve(QEasingCurve.Type.OutCubic)
        anim.start(QPropertyAnimation.DeletionPolicy.DeleteWhenStopped)


    # --- Helper to add new path rows ---
    def _add_row(self, path="", delay=0.0, mode="Not Maximized"):
        item = QListWidgetItem(self.listw)
        w = PathRow(path, delay, mode)
        item.setSizeHint(QSize(0, 50))
        self.listw.addItem(item)
        self.listw.setItemWidget(item, w)
        w.delete_btn.setIcon(themed_icon("delete.svg"))
        w.delete_btn.setToolTip("Delete this path")
        w.delete_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        w.delete_btn.setStyleSheet("border:none; border-radius:6px; padding:4px;")
        w.delete_btn.setFixedSize(32, 32)
        w.delete_btn.clicked.connect(lambda: self.listw.takeItem(self.listw.row(item)))

    # --- Inline message helper ---
    def _show_inline_message(self, text: str, color: str = "#f39c12", duration: Optional[int] = None):
        """
        Show a persistent inline message (doesn't auto-clear unless duration is given).
        """
        self.msg_label.setStyleSheet(f"font-size:12px; color:{color};")
        self.msg_label.setText(text)

        # Only clear if a duration was explicitly provided
        if duration:
            QTimer.singleShot(duration, lambda: self.msg_label.setText(""))


    def _normalize_path(self, path: str) -> str:
        """
        Normalize a path entered by the user:
        - Remove wrapping quotes (' or ")
        - Strip whitespace
        - Expand ~ and environment vars
        - Convert slashes to OS-native format
        """
        if not path:
            return ""
        path = path.strip().strip("'\"")          # remove surrounding quotes
        path = os.path.expanduser(path)           # handle ~user
        path = os.path.expandvars(path)           # handle %VAR% or $VAR
        path = os.path.normpath(path)             # fix slashes, .. etc.
        return path


    # --- Save logic ---
    
    def _save(self):
        name = (self.name_edit.text() or "").strip()
        valid_paths = []
        invalid_items: list[tuple[QListWidgetItem, PathRow, QLineEdit]] = []
        should_flash_name = False

        # --- Validate name ---
        if not name:
            should_flash_name = True
        else:
            self.name_edit.setStyleSheet(self.default_name_style)

        # --- Validate each path row ---
        for i in range(self.listw.count()):
            item = self.listw.item(i)
            row_widget = cast(Optional[PathRow], self.listw.itemWidget(item))
            if row_widget is None:
                continue

            path_edit = getattr(row_widget, "path_edit", None)
            if path_edit is None or not isinstance(path_edit, QLineEdit):
                path_edit = row_widget.findChild(QLineEdit)

            v = row_widget.value()
            raw_path = (v.get("path") or "").strip()
            norm_path = self._normalize_path(raw_path)

            if not norm_path or not os.path.exists(norm_path):
                invalid_items.append((item, row_widget, path_edit))
            else:
                v["path"] = norm_path
                valid_paths.append(v)

        num_invalid = len(invalid_items)
        no_paths_entered = not valid_paths and not invalid_items

        # --- Determine message and flash behavior ---
        if should_flash_name and no_paths_entered:
            # No name, no paths
            self._show_inline_message("Please fill name and add at least 1 path.", "#e74c3c")
            self._flash_name_border()
            return

        elif should_flash_name and num_invalid > 0:
            # Missing name + invalid paths
            if num_invalid == 1:
                msg = "Please fill name and fix invalid path."
            else:
                msg = f"Please fill name and fix {num_invalid} invalid paths."
            self._show_inline_message(msg, "#e74c3c")
            self._flash_name_border()
            for _, _, pe in invalid_items:
                if pe:
                    self._flash_widget(pe)
            first_item, _, _ = invalid_items[0]
            self.listw.scrollToItem(first_item)
            return

        elif should_flash_name:
            # Only name invalid
            self._show_inline_message("Invalid name.", "#e74c3c")
            self._flash_name_border()
            return

        elif num_invalid > 0:
            # Only paths invalid
            if num_invalid == 1:
                msg = "Path is invalid."
            else:
                msg = f"{num_invalid} paths are invalid."
            self._show_inline_message(msg, "#e74c3c")
            first_item, _, _ = invalid_items[0]
            self.listw.scrollToItem(first_item)
            if invalid_items[0][2]:
                invalid_items[0][2].setFocus()
            for _, _, pe in invalid_items:
                if pe:
                    self._flash_widget(pe)
            return

        elif not valid_paths:
            # No valid paths at all
            self._show_inline_message("Please add at least 1 valid path.", "#e74c3c")
            return

        # --- All valid ---
        if self.on_save:
            self.on_save({"name": name, "paths": valid_paths})
        self.accept()