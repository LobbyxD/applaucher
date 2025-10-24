# core/storage.py
import os, json
from PyQt6.QtCore import QStandardPaths

DATA_FILE = "launches.json"

def get_data_path() -> str:
    base_dir = QStandardPaths.writableLocation(QStandardPaths.StandardLocation.AppDataLocation)
    os.makedirs(base_dir, exist_ok=True)
    return os.path.join(base_dir, DATA_FILE)

def load_launches():
    try:
        with open(get_data_path(), "r", encoding="utf-8") as f:
            return json.load(f)
    except Exception:
        return []

def save_launches(data):
    try:
        with open(get_data_path(), "w", encoding="utf-8") as f:
            json.dump(data, f, indent=2)
    except Exception as e:
        raise RuntimeError(f"Failed to save: {e}")
