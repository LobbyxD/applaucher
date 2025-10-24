# core/app_settings.py
import os, json, sys

def get_base_dir() -> str:
    """Return correct base directory for both source and PyInstaller build."""
    if getattr(sys, 'frozen', False) and hasattr(sys, '_MEIPASS'):
        # Running from PyInstaller bundle
        return sys._MEIPASS
    # Running in normal dev environment
    return os.path.dirname(os.path.dirname(__file__))

def load_settings() -> dict:
    base_dir = get_base_dir()
    path = os.path.join(base_dir, "app_settings.json")
    if not os.path.exists(path):
        raise FileNotFoundError(f"Missing app_settings.json at: {path}")
    with open(path, "r", encoding="utf-8") as f:
        return json.load(f)

APP_SETTINGS = load_settings()