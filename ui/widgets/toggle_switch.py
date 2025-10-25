import os
from PyQt6.QtCore import QEasingCurve, QPropertyAnimation, QRect, QRectF, Qt, pyqtProperty
from PyQt6.QtGui import QBrush, QColor, QCursor, QPainter, QPixmap
from PyQt6.QtWidgets import QPushButton
from PyQt6.QtGui import QTransform



class ToggleSwitch(QPushButton):
    def __init__(self, on_icon=None, off_icon=None, initial_state=False, parent=None):
        super().__init__(parent)
        self.setCheckable(True)
        self.setChecked(initial_state)
        self.on_icon = on_icon   # 🌙 moon
        self.off_icon = off_icon # ☀️ sun
        self._rotation = 360.0 if initial_state else 0.0  # 0 = day, 180 = night
        self._rotation_anim = None

        # --- Initial animation states ---
        self._handle_position = 1 if initial_state else 0
        self._bg_color = QColor("#0f2027") if initial_state else QColor("#cfcfcf")
        self._icon_opacity = 1.0 if initial_state else 0.0  # 0=sun, 1=moon

        # --- Animations ---
        self._animation = QPropertyAnimation(self, b"handle_pos", self)
        self._animation.setDuration(300)
        self._color_anim = None
        self._icon_animation = None

        # --- UI basics ---
        self.setFixedSize(80, 28)
        self.setCursor(QCursor(Qt.CursorShape.PointingHandCursor))
        self.setStyleSheet("border: none; background: transparent;")

    # === Properties for animation ===
    def get_handle_pos(self): return self._handle_position
    def set_handle_pos(self, pos): self._handle_position = pos; self.update()
    handle_pos = pyqtProperty(float, get_handle_pos, set_handle_pos)

    def get_bg_color(self): return self._bg_color
    def set_bg_color(self, color): self._bg_color = color; self.update()
    bg_color = pyqtProperty(QColor, get_bg_color, set_bg_color)

    def get_icon_opacity(self): return self._icon_opacity
    def set_icon_opacity(self, value): self._icon_opacity = value; self.update()
    icon_opacity = pyqtProperty(float, get_icon_opacity, set_icon_opacity)

    def get_rotation(self):
        return self._rotation

    def set_rotation(self, value):
        self._rotation = value
        self.update()

    rotation = pyqtProperty(float, get_rotation, set_rotation)

    def get_blend(self):
        return getattr(self, "_blend", 0.0)
    
    def set_blend(self, value):
        self._blend = value
        self.update()

    blend = pyqtProperty(float, get_blend, set_blend)

    
    # === Drawing ===

    def paintEvent(self, event):
        radius = self.height() / 2
        margin = 3
        handle_diam = self.height() - margin * 2
        handle_x = margin + (self.width() - handle_diam - margin * 2) * self._handle_position

        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)

        # --- Dynamic gradient background (rotating sky only) ---
        rect_f = QRectF(self.rect())
        rect_f.adjust(0.5, 0.5, -0.5, -0.5)

        from PyQt6.QtGui import QLinearGradient, QTransform
        gradient = QLinearGradient(0, 0, 0, rect_f.height())
        gradient.setCoordinateMode(QLinearGradient.CoordinateMode.ObjectBoundingMode)

        # 🌞 Unchecked (day / sunrise) → 🌙 Checked (night)
        # We no longer blend colors — we switch palettes instantly, and rotation gives the motion illusion
        if self.isChecked():
            top_color = QColor("#0f2027")     # deep night
            bottom_color = QColor("#0f2027")  # darker base
        else:
            top_color = QColor("#cfcfcf")     # sunrise yellow
            bottom_color = QColor("#f39f86")  # warm orange

        gradient.setColorAt(0.0, top_color)
        gradient.setColorAt(1.0, bottom_color)

        # ✅ Rotate ONLY the gradient, not the painter
        brush = QBrush(gradient)
        t = QTransform()
        cx, cy = rect_f.center().x(), rect_f.center().y()
        t.translate(cx, cy)
        t.rotate(self._rotation)
        t.translate(-cx, -cy)
        brush.setTransform(t)


        # Border color based on average brightness
        avg = (top_color.red() + top_color.green() + top_color.blue()) // 3
        border = QColor(max(0, avg - 60), max(0, avg - 60), max(0, avg - 60))

        pen = painter.pen()
        pen.setWidth(1)
        pen.setColor(border)
        painter.setPen(pen)
        painter.setBrush(brush)
        painter.drawRoundedRect(rect_f, radius, radius)
        # Soft overlay during rotation (based on angle)
        angle_progress = (self._rotation % 180) / 180.0  # 0→1 within each half-turn
        transition_opacity = abs(0.5 - angle_progress) * 0.3  # brightest mid-spin
        if transition_opacity > 0.01:
            painter.save()
            painter.setBrush(QColor(255, 255, 255, int(255 * transition_opacity)))
            painter.setPen(Qt.PenStyle.NoPen)
            painter.drawRoundedRect(rect_f, radius, radius)
            painter.restore()



        # --- Icon rotation + cross-fade (sun↔moon) ---
        if self.on_icon and os.path.exists(self.on_icon) and self.off_icon and os.path.exists(self.off_icon):
            sun_pix = QPixmap(self.off_icon).scaled(
                16, 16,
                Qt.AspectRatioMode.KeepAspectRatio,
                Qt.TransformationMode.SmoothTransformation
            )
            moon_pix = QPixmap(self.on_icon).scaled(
                16, 16,
                Qt.AspectRatioMode.KeepAspectRatio,
                Qt.TransformationMode.SmoothTransformation
            )

            cx, cy = self.width() / 2, self.height() / 2
            x = int(cx - sun_pix.width() / 2)
            y = int(cy - sun_pix.height() / 2)

            # save state for rotation transform
            painter.save()
            painter.translate(cx, cy)
            painter.rotate(self._rotation)
            painter.translate(-cx, -cy)

            # cross-fade icons
            painter.setOpacity(1.0 - self._icon_opacity)
            painter.drawPixmap(x, y, sun_pix)
            painter.setOpacity(self._icon_opacity)
            painter.drawPixmap(x, y, moon_pix)
            painter.setOpacity(1.0)

            # ✅ properly restore painter state to avoid "Unbalanced save/restore"
            painter.restore()

        # --- Handle (white circle) ---
        handle_rect = QRect(int(handle_x), margin, int(handle_diam), int(handle_diam))
        painter.setBrush(QColor("#ffffff"))
        painter.setPen(Qt.PenStyle.NoPen)
        painter.drawEllipse(handle_rect)


    # === Behavior ===
    def mouseReleaseEvent(self, event):
        if event.button() == Qt.MouseButton.LeftButton:
            # Prevent duplicate toggling by NOT calling QPushButton.mouseReleaseEvent
            old_state = self.isChecked()
            new_state = not old_state
            self.setChecked(new_state)

            # --- Animate handle movement ---
            self._animation.stop()
            self._animation.setStartValue(self._handle_position)
            self._animation.setEndValue(1.0 if new_state else 0.0)
            self._animation.setEasingCurve(QEasingCurve.Type.InOutCubic)
            self._animation.start()

            # --- Animate background color (day → night) ---
            day = QColor("#cfcfcf")      # 🌞 sunrise
            night = QColor("#0f2027")    # 🌙 night
            self._color_anim = QPropertyAnimation(self, b"bg_color", self)
            self._color_anim.setDuration(600)
            self._color_anim.setEasingCurve(QEasingCurve.Type.InOutCubic)

            # Target = new_state (checked→night, unchecked→day)
            self._color_anim.setStartValue(self._bg_color)
            self._color_anim.setEndValue(night if new_state else day)
            self._color_anim.start()

            # --- Animate icon fade (0 = sun, 1 = moon) ---
            self._icon_animation = QPropertyAnimation(self, b"icon_opacity", self)
            self._icon_animation.setDuration(400)
            self._icon_animation.setEasingCurve(QEasingCurve.Type.InOutQuad)


            # Maintain consistent meaning:
            # old_state=False → start at sun (0), fade to moon (1)
            # old_state=True  → start at moon (1), fade to sun (0)
            self._icon_animation.setStartValue(1.0 if old_state else 0.0)
            self._icon_animation.setEndValue(0.0 if old_state else 1.0)
            self._icon_animation.start()

            # --- Animate rotation (true spin) ---
            self._rotation_anim = QPropertyAnimation(self, b"rotation", self)
            self._rotation_anim.setDuration(700)
            self._rotation_anim.setEasingCurve(QEasingCurve.Type.InOutCubic)

            # Smooth 0↔180 rotation each toggle
            target_angle = 360.0 if new_state else 0.0
            self._rotation_anim.setStartValue(self._rotation)
            self._rotation_anim.setEndValue(target_angle)
            self._rotation_anim.start()

            # Instead of only fading colors, we rotate the entire gradient
            start_angle = 360.0 if old_state else 0.0
            end_angle = 0.0 if old_state else 360.0

            self._rotation_anim.setStartValue(start_angle)
            self._rotation_anim.setEndValue(end_angle)
            self._rotation_anim.start()

            # --- Smooth background fade (blend mix) ---
            self._blend_anim = QPropertyAnimation(self, b"blend", self)
            self._blend_anim.setDuration(800)
            self._blend_anim.setEasingCurve(QEasingCurve.Type.InOutQuad)
            self._blend_anim.setStartValue(0.0 if old_state else 1.0)
            self._blend_anim.setEndValue(1.0 if new_state else 0.0)
            self._blend_anim.start()

            # Emit only once
            self.clicked.emit()

        # DO NOT CALL super().mouseReleaseEvent(event)
