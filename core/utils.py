# core/utils.py
import re

def sanitize_filename(name: str) -> str:
    """Return a Windows-safe version of a filename."""
    return re.sub(r'[<>:"/\\|?*]', "_", name).strip()
