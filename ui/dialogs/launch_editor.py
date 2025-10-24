# ui/dialogs/launch_editor.py
from typing import Optional, Dict, Any, cast
from PyQt6.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QLabel, QPushButton,
    QListWidget, QListWidgetItem, QFrame, QMessageBox, QLineEdit
)
from PyQt6.QtCore import QSize
from ui.widgets.path_row import PathRow  # LaunchEditor uses PathRow rows

MODES = ["Not Maximized", "Maximized", "Minimized"]

class LaunchEditor(QDialog):
    def __init__(self, existing: Optional[Dict[str, Any]] = None, dark: bool = True, on_save=None):
        super().__init__()
        self.setWindowTitle("Add / Edit Launch")
        self.setMinimumSize(740, 580)
        self.setModal(True)
        self.on_save = on_save

        header = QLabel("🧩  Add / Edit Launch")
        header.setStyleSheet("font-size:22px; font-weight:600; margin-bottom: 6px;")

        card = QFrame()
        card.setObjectName("card")

        # --- Name field ---
        name_lbl = QLabel("App Launcher Name")
        self.name_edit = QLineEdit(existing["name"] if existing else "")
        helper = QLabel("Name displayed on the main launcher list.")
        helper.setStyleSheet("font-size:12px; opacity:0.75;")

        name_box = QVBoxLayout()
        name_box.addWidget(name_lbl)
        name_box.addWidget(self.name_edit)
        name_box.addWidget(helper)

        # --- Paths list ---
        paths_lbl = QLabel("Paths to Launch")
        self.listw = QListWidget()
        self.listw.setDragDropMode(QListWidget.DragDropMode.InternalMove)

        # preload rows if editing
        for p in (existing["paths"] if existing else []):
            self._add_row(p.get("path", ""), p.get("delay", 0.0), p.get("start_option", "Not Maximized"))

        add_btn = QPushButton("➕  Add Path")
        add_btn.clicked.connect(lambda: self._add_row())

        inner = QVBoxLayout(card)
        inner.setContentsMargins(16, 16, 16, 16)
        inner.setSpacing(10)
        inner.addLayout(name_box)

        # ✅ Proper horizontal line
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
        w.delete_btn.clicked.connect(lambda: self.listw.takeItem(self.listw.row(item)))

    def _save(self):
        name = (self.name_edit.text() or "").strip() or "Untitled"
        paths = []
        for i in range(self.listw.count()):
            it = self.listw.item(i)
            w = cast(Optional[PathRow], self.listw.itemWidget(it))  # ✅ Cast safely
            if w is None:
                continue
            v = w.value()
            if v["path"]:
                paths.append(v)
        if not paths:
            QMessageBox.warning(self, "Empty", "Please add at least one path.")
            return
        if self.on_save:
            self.on_save({"name": name, "paths": paths})
        self.accept()
