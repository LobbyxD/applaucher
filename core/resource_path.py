import os
import sys

def resource_path(rel_path: str) -> str:
    """
    Get absolute path to resource, works for dev and PyInstaller.
    """
    if getattr(sys, "frozen", False):
        return os.path.join(sys._MEIPASS, rel_path)
    return os.path.abspath(rel_path)
