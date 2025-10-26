# ui/widgets/style_helpers.py
import os

from PyQt6.QtWidgets import (QComboBox, QDoubleSpinBox, QFrame, QLabel,
                             QLineEdit, QPushButton, QWidget)

from ui.theme_manager import ThemeManager

def apply_button_style(btn: QPushButton) -> None:
        """Apply a consistent border, radius, and hover color to PathRow buttons."""
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

def apply_input_style(input_field: QLineEdit) -> None:
    """Modern, theme-aware flat QLineEdit with readable selection."""
    colors = ThemeManager.load_themes()["dark" if ThemeManager.is_dark() else "light"]
    base = colors["Base"]
    hover = colors["Hover"]
    border = colors["Border"]
    text = colors["Text"]

    # Use contrasting text for selection depending on theme
    selection_bg = hover
    selection_text = "#ffffff" if ThemeManager.is_dark() else "#000000"

    input_field.setStyleSheet(f"""
        QLineEdit {{
            background-color: {base};
            border: 1px solid {border};
            border-radius: 6px;
            padding: 6px 8px;
            color: {text};
            selection-background-color: {selection_bg};
            selection-color: {selection_text};
            font-size: 13px;
        }}
        QLineEdit:hover {{
            border: 1px solid {hover};
        }}
        QLineEdit:focus {{
            border: 1px solid {hover};
            background-color: {base};
        }}
    """)

def apply_spinbox_style(spinbox: QDoubleSpinBox) -> None:
    """Modern, flat QDoubleSpinBox styled to match theme with readable selection."""
    colors = ThemeManager.load_themes()["dark" if ThemeManager.is_dark() else "light"]
    base = colors["Base"]
    hover = colors["Hover"]
    border = colors["Border"]
    text = colors["Text"]

    theme_dir = "dark" if ThemeManager.is_dark() else "light"
    arrow_up = os.path.join("resources", "icons", f"{theme_dir} icons", "spin_up.svg").replace("\\", "/")
    arrow_down = os.path.join("resources", "icons", f"{theme_dir} icons", "spin_down.svg").replace("\\", "/")

    selection_bg = hover
    selection_text = "#ffffff" if ThemeManager.is_dark() else "#000000"

    spinbox.setStyleSheet(f"""
        QDoubleSpinBox {{
            background-color: {base};
            border: 1px solid {border};
            border-radius: 6px;
            padding: 4px 22px 4px 8px; /* space for arrows */
            color: {text};
            font-size: 13px;
            selection-background-color: {selection_bg};
            selection-color: {selection_text};
        }}
        QDoubleSpinBox:hover {{
            border: 1px solid {hover};
        }}
        QDoubleSpinBox:focus {{
            border: 1px solid {hover};
            background-color: {base};
        }}
        QDoubleSpinBox::up-button {{
            subcontrol-origin: border;
            subcontrol-position: top right;
            width: 18px;
            border: none;
            background: transparent;
        }}
        QDoubleSpinBox::down-button {{
            subcontrol-origin: border;
            subcontrol-position: bottom right;
            width: 18px;
            border: none;
            background: transparent;
        }}
        QDoubleSpinBox::up-arrow {{
            image: url({arrow_up});
            width: 10px;
            height: 10px;
        }}
        QDoubleSpinBox::down-arrow {{
            image: url({arrow_down});
            width: 10px;
            height: 10px;
        }}
        QDoubleSpinBox::up-arrow:hover,
        QDoubleSpinBox::down-arrow:hover {{
            background-color: {hover};
            border-radius: 3px;
        }}
    """)

def apply_combobox_style(combo: QComboBox) -> None:
    """Unified modern combo style that auto-refreshes on theme change."""
    colors = ThemeManager.load_themes()["dark" if ThemeManager.is_dark() else "light"]
    base = colors["Base"]
    hover = colors["Hover"]
    border = colors["Border"]
    text = colors["Text"]
    window = colors["Window"]

    theme_dir = "dark" if ThemeManager.is_dark() else "light"
    arrow_down = os.path.join("resources", "icons", f"{theme_dir} icons", "spin_down.svg").replace("\\", "/")

    combo.setStyleSheet(f"""
        QComboBox {{
            background-color: {base};
            border: 1px solid {border};
            border-radius: 8px;
            padding: 6px 28px 6px 10px;
            color: {text};
            font-size: 13px;
        }}
        QComboBox:hover {{
            border: 1px solid {hover};
        }}
        QComboBox::drop-down {{
            subcontrol-origin: padding;
            subcontrol-position: top right;
            width: 22px;
            background: transparent;
        }}
        QComboBox::down-arrow {{
            image: url({arrow_down});
            width: 12px;
            height: 12px;
        }}
        QComboBox QAbstractItemView {{
            background-color: {window};
            border: 1px solid {border};
            border-radius: 8px;
            padding: 4px;
            margin-top: 3px;
            outline: none;
        }}
        QComboBox QAbstractItemView::item {{
            padding: 6px 12px;
            border-radius: 6px;
            color: {text};
        }}
        QComboBox QAbstractItemView::item:hover {{
            background-color: {hover};
        }}
        QComboBox QAbstractItemView::item:selected {{
            background-color: {hover};
            color: {text};
        }}
    """)

    # Ensure it updates live on theme change
    if hasattr(ThemeManager, "instance"):
        ThemeManager.instance().theme_changed.connect(lambda _: apply_combobox_style(combo))


def apply_frame_style(frame: QFrame, object_name: str) -> None:
    """Apply consistent bordered background to frame containers."""
    colors = ThemeManager.load_themes()["dark" if ThemeManager.is_dark() else "light"]
    border, base, hover = colors["Border"], colors["Base"], colors["Hover"]
    frame.setStyleSheet(f"""
        QFrame#{object_name} {{
            border: 1px solid {border};
            border-radius: 8px;
            background-color: {base};
            margin-top: 4px;
        }}
        QFrame#{object_name}:hover {{
            border: 1px solid {hover};
        }}
    """)

def apply_label_style(label: QLabel, bold=False, underline=False, size=14) -> None:
    """Apply theme-synced label text style."""
    colors = ThemeManager.load_themes()["dark" if ThemeManager.is_dark() else "light"]
    style = f"color: {colors['Text']}; font-size:{size}px;"
    if bold:
        style += " font-weight:600;"
    if underline:
        style += " text-decoration: underline;"
    label.setStyleSheet(style)
    
def apply_tooltip_style(widget: QWidget) -> None:
    """Apply consistent theme-aware tooltip styling globally on a widget or window."""
    colors = ThemeManager.load_themes()["dark" if ThemeManager.is_dark() else "light"]
    bg = colors["Hover"]
    text = colors["Text"]
    border = colors["Border"]

    # Append QToolTip styling to the widget’s existing stylesheet
    widget.setStyleSheet(widget.styleSheet() + f"""
        QToolTip {{
            background-color: {bg};
            color: {text};
            border: 1px solid {border};
            border-radius: 6px;
            padding: 4px 8px;
        }}
    """)