# core/storage.py
import json
import os

from core.app_settings import APP_SETTINGS

# ==========================================================
# Fixed, explicit AppData path (no QStandardPaths)
# ==========================================================
APP_NAME = APP_SETTINGS.get("app_name", "App Launcher")
BASE_DIR = os.path.join(os.environ.get("APPDATA", ""), APP_NAME)
LAUNCHERS_FILE_NAME = "launchers_config.json"
DATA_PATH = os.path.join(BASE_DIR, LAUNCHERS_FILE_NAME)

# Make sure folder exists; recreate if deleted
os.makedirs(BASE_DIR, exist_ok=True)

# ==========================================================
# Core helpers
# ==========================================================
def get_data_path() -> str:
    """Return absolute path for launchers_config.json."""
    # Recreate folder if user deleted it during runtime
    if not os.path.exists(BASE_DIR):
        os.makedirs(BASE_DIR, exist_ok=True)
    return DATA_PATH


def load_launches():
    """Load launcher data from disk. Returns [] if file missing or broken."""
    path = get_data_path()
    if not os.path.isfile(path):
        return []
    try:
        with open(path, "r", encoding="utf-8") as f:
            return json.load(f)
    except Exception:
        return []


def save_launches(data):
    """Save launcher data safely into the unified AppData folder."""
    path = get_data_path()
    try:
        with open(path, "w", encoding="utf-8") as f:
            json.dump(data, f, indent=2)
    except Exception as e:
        raise RuntimeError(f"Failed to save launchers: {e}")
