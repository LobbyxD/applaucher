from PyQt6.QtCore import QPoint, QSize, Qt
from PyQt6.QtWidgets import QFrame, QListWidget, QListWidgetItem


class DraggableList(QListWidget):
    """
    Crash-proof drag/reorder:
    - NO list mutations while mouse is down
    - NO widget detaches/deletes until mouse release
    - Uses a lightweight overlay ghost (no grab())
    """

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.setSpacing(4)
        self.viewport().setCursor(Qt.CursorShape.PointingHandCursor)

        # drag state
        self._dragging = False
        self._press_pos = QPoint()
        self._start_row = -1
        self._target_row = -1
        self._ghost = None          # QFrame overlay
        self._ghost_height = 0

    # ---------- Mouse handlers ----------
    def mousePressEvent(self, event):
        if event.button() == Qt.MouseButton.LeftButton:
            self._press_pos = event.position().toPoint()
            it = self.itemAt(self._press_pos)
            self._start_row = self.row(it) if it else -1
            self._target_row = self._start_row
        super().mousePressEvent(event)

    def mouseMoveEvent(self, event):
        if not (event.buttons() & Qt.MouseButton.LeftButton) or self._start_row < 0:
            return super().mouseMoveEvent(event)

        # only start drag after threshold
        if not self._dragging:
            dx = abs(event.position().x() - self._press_pos.x())
            dy = abs(event.position().y() - self._press_pos.y())
            if dx <= 3 and dy <= 3:
                return super().mouseMoveEvent(event)
            self._begin_drag_visuals()
            self._dragging = True

        if not self._ghost:
            return

        # move ghost vertically within viewport
        y = int(event.position().y() - self._ghost_height // 2)
        y = max(0, min(y, self.viewport().height() - self._ghost_height))
        self._ghost.move(0, y)

        # compute candidate row but DO NOT mutate list
        hover_it = self.itemAt(event.position().toPoint())
        if hover_it:
            self._target_row = self.row(hover_it)
        else:
            # if below all items, drop at end
            self._target_row = self.count() - 1

    def mouseReleaseEvent(self, event):
        try:
            if self._dragging and self._start_row >= 0:
                self._finish_reorder()
        finally:
            self._end_drag_visuals()
            self._dragging = False
            self._start_row = -1
            self._target_row = -1
            super().mouseReleaseEvent(event)

    # ---------- Internals ----------
    def _begin_drag_visuals(self):
        """Show a simple overlay ghost matching the row rect. No list mutations."""
        it = self.item(self._start_row)
        if not it:
            return
        rect = self.visualItemRect(it)

        # Lightweight ghost: no QWidget.grab()
        self._ghost = QFrame(self.viewport())
        self._ghost.setGeometry(rect)
        self._ghost_height = rect.height()
        self._ghost.setStyleSheet(
            "background: rgba(100,150,255,0.15); "
            "border: 1px dashed rgba(100,150,255,0.6); "
            "border-radius: 6px;"
        )
        self._ghost.show()

    def _end_drag_visuals(self):
        if self._ghost:
            self._ghost.deleteLater()
            self._ghost = None
        self.viewport().update()

    def _finish_reorder(self):
        """Reorder items by cloning data instead of moving widgets."""
        n = self.count()
        if n <= 0:
            return

        src = max(0, min(self._start_row, n - 1))
        dst = max(0, min(self._target_row if self._target_row >= 0 else src, n - 1))
        if src == dst:
            return

        # Get the source widget and its data
        src_item = self.item(src)
        src_widget = self.itemWidget(src_item)
        if not src_widget:
            return
        data = src_widget.value()

        # Remove the original
        self.takeItem(src)
        src_widget.deleteLater()

        # Recreate a fresh PathRow widget at destination
        from ui.widgets.path_row import PathRow
        new_item = QListWidgetItem()
        new_item.setSizeHint(QSize(0, 50))
        new_widget = PathRow(
            data.get("path", ""),
            data.get("delay", 0.0),
            data.get("start_option", "Normal"),
        )

        # Insert at destination
        self.insertItem(dst, new_item)
        self.setItemWidget(new_item, new_widget)

        # Refresh UI
        self.viewport().update()
        self.updateGeometry()
        self.repaint()
