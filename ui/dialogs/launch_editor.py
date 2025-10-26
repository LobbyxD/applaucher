import os
from typing import Any, Dict, Optional, cast

from PyQt6.QtCore import QEasingCurve, QPropertyAnimation, QSize, Qt, QTimer
from PyQt6.QtGui import QColor
from PyQt6.QtWidgets import (QDialog, QFrame, QGraphicsColorizeEffect,
                             QHBoxLayout, QLabel, QLineEdit, QListWidget,
                             QListWidgetItem, QPushButton, QSizePolicy,
                             QToolButton, QVBoxLayout, QWidget)

from ui.icon_loader import themed_icon
from ui.theme_manager import ThemeManager
from ui.widgets.draggable_list import DraggableList
from ui.widgets.path_row import PathRow

MODES = ["Normal", "Maximized", "Minimized"]

class LaunchEditor(QDialog):
    def __init__(
        self,
        existing: Optional[Dict[str, Any]] = None,
        dark: bool = True,
        on_save=None,
        parent: Optional[QWidget] = None,
    ):
        # ✅ Always initialize the QDialog base first
        super().__init__(parent)

        # ✅ Now it's safe to access QWidget methods
        if existing:
            name = existing.get("name", "Launcher")
            self.setWindowTitle(f"Edit {name}")
        else:
            self.setWindowTitle("Create Launcher")

        self.setMinimumSize(740, 580)
        self.setModal(True)
        self.on_save = on_save

        # === Theme setup (define first, call later) ===
        def apply_input_theme():
            all_themes = ThemeManager.load_themes()
            dark = ThemeManager.is_dark()
            colors = all_themes["dark" if dark else "light"]

            border = colors["Border"]
            base = colors["Base"]
            text = colors["Text"]

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

            # Apply to inputs if already created
            if hasattr(self, "name_edit"):
                self.name_edit.setStyleSheet(self.default_name_style)
            if hasattr(self, "listw"):
                for i in range(self.listw.count()):
                    row = self.listw.itemWidget(self.listw.item(i))
                    if row:
                        for edit in row.findChildren(QLineEdit):
                            edit.setStyleSheet(self.default_name_style)

        def apply_tooltip_theme():
            """Apply tooltip color scheme based on current theme."""
            colors = ThemeManager.load_themes()["dark" if ThemeManager.is_dark() else "light"]
            bg = colors["Hover"]
            text = colors["Text"]
            border = colors["Border"]

            # Qt’s tooltip uses the global palette stylesheet, so we override globally
            self.setStyleSheet(self.styleSheet() + f"""
                QToolTip {{
                    background-color: {bg};
                    color: {text};
                    border: 1px solid {border};
                    border-radius: 6px;
                    padding: 4px 8px;
                }}
            """)

        # === UI setup ===
        card = QFrame()
        card.setObjectName("card")

        # --- Name field ---
        name_lbl = QLabel("Launcher Name")
        name_lbl.setStyleSheet("font-weight: 700;")
        name_container = QFrame()
        name_container.setStyleSheet("border: none;")
        name_layout = QHBoxLayout(name_container)
        name_layout.setContentsMargins(0, 0, 0, 0)
        name_layout.setSpacing(0)

        # QLineEdit
        self.name_edit = QLineEdit(existing["name"] if existing else "")
        self.name_edit.setPlaceholderText("Enter launcher name...")
        self.name_edit.setMinimumHeight(32)
        name_layout.addWidget(self.name_edit)

        # Apply theme after creating name_edit
        apply_input_theme()
        apply_tooltip_theme()

        # Connect live updates
        ThemeManager.instance().theme_changed.connect(
            lambda _: (apply_input_theme(), apply_tooltip_theme(), self._refresh_button_styles(), self._refresh_list_container())
        )

        # --- Info icon ---
        self._name_trailing_action = self.name_edit.addAction(
            themed_icon("info-solid-full.svg"),
            QLineEdit.ActionPosition.TrailingPosition,
        )
        self._name_trailing_action.setToolTip("Name displayed on the main launcher list.")
        self._name_trailing_action.setEnabled(False)

        # --- Name row layout ---
        name_box = QHBoxLayout()
        name_box.setContentsMargins(0, 0, 0, 0)
        name_box.setSpacing(8)
        name_box.addWidget(name_lbl)
        name_box.addWidget(name_container, 1)

        # --- Paths list + Add button row ---
        paths_row = QHBoxLayout()
        paths_row.setContentsMargins(0, 0, 0, 0)
        paths_row.setSpacing(8)

        paths_lbl = QLabel("Paths to Launch")
        paths_lbl.setStyleSheet("font-weight: 700;")

        add_btn = QPushButton()
        add_btn.setIcon(themed_icon("add.svg"))
        add_btn.setToolTip("Add new path")
        add_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        add_btn.setFixedSize(36, 36)
        self._apply_button_style(add_btn)

        paths_row.addWidget(paths_lbl)
        paths_row.addStretch(1)       # push button to the right
        paths_row.addWidget(add_btn)

        # --- List widget setup ---
        self.listw = DraggableList()
        self.listw.setSelectionMode(QListWidget.SelectionMode.SingleSelection)
        self.listw.setDragEnabled(False)
        self.listw.setAcceptDrops(False)
        self.listw.setDropIndicatorShown(False)
        # Remove default sunken border and background
        self.listw.setFrameShape(QFrame.Shape.NoFrame)
        colors = ThemeManager.load_themes()["dark" if ThemeManager.is_dark() else "light"]
        base = colors["Base"]
        border = colors["Border"]

        self.listw.setStyleSheet(f"""
            QListWidget {{
                background-color: transparent;
                border: none;
            }}
            QListWidget::item {{
                background-color: transparent;
                border: none;
                margin: 2px;
            }}
        """)


        self.listw.setCursor(Qt.CursorShape.ArrowCursor)
        self.listw.viewport().setCursor(Qt.CursorShape.ArrowCursor)

        add_btn.clicked.connect(lambda: self._add_row())


        # --- Themed list background and item styling ---
        colors = ThemeManager.load_themes()["dark" if ThemeManager.is_dark() else "light"]
        base = colors["Base"]
        window = colors["Window"]
        hover = colors["Hover"]
        border = colors["Border"]

        self.listw.setStyleSheet(f"""
            QListWidget {{
                background-color: {window};
                border: 1px solid {border};
                border-radius: 8px;
                outline: none;
            }}
            QListWidget::item {{
                background: transparent;
                border: none;
                margin: 3px;
                padding: 0px;
            }}
            QListWidget::item:selected {{
                background-color: transparent;  /* PathRow handles highlight */
                border: none;
            }}
        """)

        self.listw.setFrameShape(QFrame.Shape.NoFrame)
        self.listw.setAutoFillBackground(False)
        self.listw.setAttribute(Qt.WidgetAttribute.WA_StyledBackground, True)

        # Connect selection changes for theme-based highlight
        self.listw.itemSelectionChanged.connect(self._update_row_selection)

        # --- Preload rows ---
        for p in (existing["paths"] if existing else []):
            self._add_row(p.get("path", ""), p.get("delay", 0.0), p.get("start_option", "Normal"))

        # --- Inner layout ---
        inner = QVBoxLayout(card)
        inner.setContentsMargins(16, 16, 16, 0)
        inner.setSpacing(5)
        inner.addLayout(name_box)

        divider = QFrame()
        divider.setFrameShape(QFrame.Shape.HLine)
        divider.setFrameShadow(QFrame.Shadow.Sunken)
        inner.addWidget(divider)

        # Add the row (label + button) above the list
        inner.addLayout(paths_row)

        # --- Themed container for the path list ---
        list_container = QFrame()
        list_container.setObjectName("pathListContainer")
        list_layout = QVBoxLayout(list_container)
        list_layout.setContentsMargins(6, 6, 6, 6)
        list_layout.addWidget(self.listw)
        inner.addWidget(list_container, 1)

        # Apply initial container style
        self._apply_list_container_style(list_container)

        # --- Footer (inside card) ---
        save_btn = QPushButton("Save")
        cancel_btn = QPushButton("Cancel")
        self._apply_button_style(save_btn)
        self._apply_button_style(cancel_btn)
        padding = "5 10 5 10"
        margin = "0 0 5 0"
        save_btn.setStyleSheet(f"padding: {padding}px; margin: {margin}px;")
        cancel_btn.setStyleSheet(f"padding: {padding}px; margin: {margin}px;")

        
        # --- Footer (centered inside card) ---
        footer = QHBoxLayout()
        footer.setContentsMargins(0, 4, 0, 0)  # small top margin only
        footer.setSpacing(8)  # tighten space between buttons

        # Center both buttons as a group
        group = QHBoxLayout()
        group.setSpacing(8)
        group.addWidget(cancel_btn)
        group.addWidget(save_btn)

        footer.addStretch(1)
        footer.addLayout(group)
        footer.addStretch(1)

        # Add footer inside the card, below list_container
        inner.addLayout(footer)

        # --- Root layout ---
        root = QVBoxLayout(self)
        root.setContentsMargins(0, 18, 0, 10)
        root.setSpacing(5)

        # --- Inline message (right aligned with clean padding) ---
        msg_container = QHBoxLayout()
        msg_container.setContentsMargins(0, 0, 18, 0)  # ⬅ right padding from window edge
        msg_container.setSpacing(0)

        self.msg_label = QLabel("")
        self.msg_label.setAlignment(Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignVCenter)
        self.msg_label.setStyleSheet("font-size:12px; color:#e74c3c;")
        msg_container.addWidget(self.msg_label, alignment=Qt.AlignmentFlag.AlignRight)

        root.addLayout(msg_container)

        center_layout = QHBoxLayout()
        center_layout.setContentsMargins(14, 0, 14, 0)
        center_layout.setSpacing(0)
        card.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Expanding)
        center_layout.addWidget(card, 1)
        root.addLayout(center_layout, 1)

        # Message label below card (optional, can also move inside if you prefer)
        root.addWidget(self.msg_label)



        cancel_btn.clicked.connect(self.reject)
        save_btn.clicked.connect(self._save)

        # === Shared Styling Helper (theme-aware) ===
    def _apply_button_style(self, btn: QPushButton):
        colors = ThemeManager.load_themes()["dark" if ThemeManager.is_dark() else "light"]
        border = colors["Border"]
        hover = colors["Hover"]
        base = colors["Button"]
        text = colors["ButtonText"]

        btn.setStyleSheet(f"""
            QPushButton {{
                border: 1px solid {border};
                border-radius: 6px;
                background-color: {base};
                color: {text};
                padding: 4px;
            }}
            QPushButton:hover {{
                background-color: {hover};
            }}
        """)

        # === Themed Path List Container ===
    def _apply_list_container_style(self, container: QFrame):
        """Apply theme-based border and background for the path list area."""
        colors = ThemeManager.load_themes()["dark" if ThemeManager.is_dark() else "light"]
        border = colors["Border"]
        base = colors["Base"]
        hover = colors["Hover"]

        container.setStyleSheet(f"""
            QFrame#pathListContainer {{
                border: 1px solid {border};
                border-radius: 8px;
                background-color: {base};
                margin-top: 4px;
            }}
            QFrame#pathListContainer:hover {{
                border: 1px solid {hover};
            }}
        """)

        # ✅ Set cursor explicitly (Qt API, not QSS)
        container.setCursor(Qt.CursorShape.ArrowCursor)

    def _refresh_button_styles(self):
        for btn in self.findChildren(QPushButton):
            self._apply_button_style(btn)

    def _refresh_list_container(self):
        """Reapply list container theme when toggled."""
        container = self.findChild(QFrame, "pathListContainer")
        if container:
            self._apply_list_container_style(container)


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
    def _add_row(self, path=None, delay=None, mode=None):
        item = QListWidgetItem(self.listw)
        w = PathRow(path or "", delay, mode)
        item.setSizeHint(QSize(0, 50))
        self.listw.addItem(item)
        self.listw.setItemWidget(item, w)
        w.delete_btn.setIcon(themed_icon("delete.svg"))
        w.delete_btn.setToolTip("Delete this path")
        w.delete_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        self._apply_button_style(w.delete_btn)
        w.delete_btn.setFixedSize(32, 32)
        w.delete_btn.clicked.connect(lambda: self.listw.takeItem(self.listw.row(item)))

    # --- Inline message helper ---
    def _show_inline_message(self, text: str, color: str = "#f39c12", duration: Optional[int] = None):
        """
        Show a persistent inline message (doesn't auto-clear unless duration is given).
        """
        self.msg_label.setStyleSheet(f"font-size:12px; color:{color}; padding-right: 15px;")
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

    def _update_row_selection(self):
        """Apply theme-based highlight to selected PathRows."""
        colors = ThemeManager.load_themes()["dark" if ThemeManager.is_dark() else "light"]
        normal_bg = colors["Window"]
        selected_bg = colors["Hover"]

        for i in range(self.listw.count()):
            item = self.listw.item(i)
            row = self.listw.itemWidget(item)
            if not row:
                continue
            row.setStyleSheet(f"""
                background-color: {selected_bg if item.isSelected() else normal_bg};
                border-radius: 8px;
            """)
