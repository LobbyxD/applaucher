# ui/widgets/themed_combobox.py
from PyQt6.QtCore import Qt
from PyQt6.QtGui import QColor, QPalette
from PyQt6.QtWidgets import QComboBox, QFrame, QListView

from ui.theme_manager import ThemeManager

class ThemedComboBox(QComboBox):
    """Theme-synced combo box with popup that truly matches App Launcher color scheme."""
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

        # Custom view for styling control
        view = QListView()
        view.setSpacing(2)
        view.setUniformItemSizes(True)
        view.setVerticalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        view.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        view.setEditTriggers(QListView.EditTrigger.NoEditTriggers)
        view.setFrameShape(QFrame.Shape.NoFrame)
        self.setView(view)

        self._apply_theme_colors()

    def _apply_theme_colors(self):
        """Applies ThemeManager colors directly to popup palette (ensures consistency)."""
        colors = ThemeManager.load_themes()["dark" if ThemeManager.is_dark() else "light"]

        base = QColor(colors["Base"])
        text = QColor(colors["Text"])
        window = QColor(colors["Window"])
        highlight = QColor(colors["Hover"])

        pal = self.palette()
        pal.setColor(QPalette.ColorRole.Base, base)
        pal.setColor(QPalette.ColorRole.Window, window)
        pal.setColor(QPalette.ColorRole.Text, text)
        pal.setColor(QPalette.ColorRole.ButtonText, text)
        pal.setColor(QPalette.ColorRole.Highlight, highlight)
        pal.setColor(QPalette.ColorRole.HighlightedText, text)
        self.setPalette(pal)

    def showPopup(self):
        """Ensure popup adopts theme palette and aligns perfectly with combo field."""
        self._apply_theme_colors()
        view = self.view()
        popup = view.window()

        # --- Ensure it's frameless, no drop shadow ---
        popup.setWindowFlags(
            Qt.WindowType.Popup
            | Qt.WindowType.FramelessWindowHint
            | Qt.WindowType.NoDropShadowWindowHint
        )

        # ✅ Make popup *truly transparent* under the styled QListView
        popup.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground, True)
        popup.setAttribute(Qt.WidgetAttribute.WA_StyledBackground, True)
        view.setFrameShape(QFrame.Shape.NoFrame)

        # --- Theme colors ---
        colors = ThemeManager.load_themes()["dark" if ThemeManager.is_dark() else "light"]
        border = colors["Border"]
        bg = colors["Base"]
        hover = colors["Hover"]
        text = colors["Text"]

        # --- Style the inner view only (not the popup window) ---
        view.setStyleSheet(f"""
            QListView {{
                background-color: {bg};
                border: 1px solid {border};
                border-radius: 8px;
                outline: none;
            }}
            QListView::item {{
                padding: 6px 10px;
                border-radius: 6px;
                color: {text};
            }}
            QListView::item:hover {{
                background-color: {hover};
            }}
            QListView::item:selected {{
                background-color: {hover};
                color: {text};
            }}
        """)

        # --- Align popup exactly under combo field ---
        field_rect = self.rect()
        global_pos = self.mapToGlobal(field_rect.bottomLeft())
        popup.move(global_pos.x(), global_pos.y() + 1)

        # --- Show popup first (creates the native window) ---
        super().showPopup()

        # --- Apply rounded mask to the popup ---
        from PyQt6.QtGui import QRegion, QPainterPath
        from PyQt6.QtCore import QRectF

        popup_rect = QRectF(popup.rect())
        radius = 8
        path = QPainterPath()
        path.addRoundedRect(popup_rect, radius, radius)
        region = QRegion(path.toFillPolygon().toPolygon())
        popup.setMask(region)


