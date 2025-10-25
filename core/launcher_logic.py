import asyncio
import datetime
import os
import subprocess

import psutil
import win32con
import win32process
from PyQt6.QtCore import QStandardPaths
from ui.theme_manager import ThemeManager

# --- Debug Logging ---
def log(message: str, exc: Exception | None = None):
    """
    Append a detailed log entry to %APPDATA%/App Launcher/log.txt
    Only runs when ThemeManager.get_setting('debug_logging', True) is True.
    Truncates file when it grows beyond 1 MB.
    """
    try:
        if not ThemeManager.get_setting("debug_logging", True):
            return

        # Ensure app dir exists and resolve log path via ThemeManager
        ThemeManager.ensure_appdir()
        log_dir = ThemeManager.APP_DIR
        log_path = os.path.join(log_dir, "log.txt")

        # Truncate if > 1MB
        if os.path.exists(log_path) and os.path.getsize(log_path) > 1_000_000:
            with open(log_path, "w", encoding="utf-8") as f:
                f.write(f"[{datetime.datetime.now():%Y-%m-%d %H:%M:%S}] 🔄 Log truncated (>1MB)\n")

        # Append entry
        ts = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        with open(log_path, "a", encoding="utf-8") as f:
            f.write(f"[{ts}] {message}\n")
            if exc is not None:
                f.write(f"    Exception: {exc.__class__.__name__}: {exc}\n")
    except Exception:
        # Never allow logging to break the app
        pass

async def launch_app(path: str, delay: float, start_option: str):
    """Launch an app or batch file with correct visibility behavior."""
    # --- Normalize path to handle both quoted/unquoted inputs ---
    path = path.strip().strip('"').strip("'")

    si = subprocess.STARTUPINFO()
    si.dwFlags |= win32con.STARTF_USESHOWWINDOW

    if start_option == "Maximized":
        si.wShowWindow = win32con.SW_SHOWMAXIMIZED
    elif start_option == "Minimized":
        si.wShowWindow = win32con.SW_SHOWMINNOACTIVE
    else:
        si.wShowWindow = win32con.SW_SHOWNORMAL

    creation_flags = 0
    if start_option == "Minimized":
        creation_flags = win32process.DETACHED_PROCESS

    # Detect .bat files and use cmd /c to run them silently
    if path.lower().endswith(".bat"):
        subprocess.Popen(
            ["cmd.exe", "/c", path],
            startupinfo=si,
            creationflags=creation_flags
        )
    else:
        subprocess.Popen([path], startupinfo=si, creationflags=creation_flags)

    # don't delay here, delays handled in sequence


async def run_launch_sequence(apps, progress_cb=None):
    """Sequentially run apps, showing a *single-line live countdown* between launches."""
    total = len(apps)
    log(f"▶️ Run sequence start: {total} item(s)")

    for idx, app in enumerate(apps, start=1):
        path = app["path"]
        delay = float(app["delay"])
        opt = app["start_option"]

        # --- UI progress line (preserved) ---
        if progress_cb:
            progress_cb(f"Launching {idx}/{total}: {path} ({opt})...")

        # --- Logging (added) ---
        log(f"▶️ Launching {idx}/{total}: path='{path}', mode='{opt}', next_delay={delay}s")

        try:
            await launch_app(path, 0, opt)
            log(f"✅ Launched OK: {path}")
        except Exception as e:
            log(f"❌ Launch failed: {path}", e)
            if progress_cb:
                progress_cb(f"❌ Error launching {path}: {e}")
            continue

        # --- Countdown between apps (preserved UX) ---
        if idx < total and delay > 0:
            log(f"⏳ Waiting {delay}s before next app")
            for remaining in range(int(delay), 0, -1):
                if progress_cb:
                    # overwrite same line (no newline)
                    progress_cb(f"⏳ Waiting {remaining:>2}s before next...", end="\r")
                await asyncio.sleep(1)

            # Clear line once countdown finishes
            if progress_cb:
                progress_cb(" " * 60, end="\r")

    log("✅ Run sequence done")
    if progress_cb:
        progress_cb("✅ Done.")
