import asyncio
import datetime
import os
import subprocess

import win32con

try:
    from win32com.shell import shell, shellcon
except ImportError:
    shell = None
    shellcon = None

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
    """Launch any file as if double-clicked in Explorer, fully silent (no cmd window)."""
    # --- Normalize path ---
    path = path.strip().strip('"').strip("'")

    si = subprocess.STARTUPINFO()
    si.dwFlags |= win32con.STARTF_USESHOWWINDOW

    if start_option == "Maximized":
        si.wShowWindow = win32con.SW_SHOWMAXIMIZED
    elif start_option == "Minimized":
        si.wShowWindow = win32con.SW_SHOWMINNOACTIVE
    else:
        si.wShowWindow = win32con.SW_SHOWNORMAL

    # --- Launch logic ---
    try:
        ext = os.path.splitext(path)[1].lower()

        # # 🧩 CASE 1: .bat or .cmd (silent)
        # if ext in (".bat", ".cmd"):
        #     # Run batch silently with CREATE_NO_WINDOW
        #     CREATE_NO_WINDOW = 0x08000000
        #     subprocess.Popen(
        #         ["cmd.exe", "/c", path],
        #         creationflags=CREATE_NO_WINDOW,
        #         startupinfo=si
        #     )


        # # 🧩 CASE 2: .exe or .lnk (apps and shortcuts)
        # elif ext in (".exe", ".lnk"):
        #     shell.ShellExecuteEx(
        #         fMask=shellcon.SEE_MASK_NO_CONSOLE,
        #         lpVerb="open",
        #         lpFile=path,
        #         nShow=si.wShowWindow
        #     )

        # # 🧩 CASE 3: Any other file (folder, pdf, image, url, etc.)
        # else:
        # Use same ShellExecuteEx call to simulate Explorer double-click
            # shell.ShellExecuteEx(
            #     fMask=shellcon.SEE_MASK_NO_CONSOLE,
            #     lpVerb="open",
            #     lpFile=path,
            #     nShow=win32con.SW_SHOWNORMAL
            # )
        if shell:
            bat_dir = os.path.dirname(path)
            shell.ShellExecuteEx(
                fMask=shellcon.SEE_MASK_NO_CONSOLE,
                lpVerb="open",
                lpFile=path,
                lpDirectory=bat_dir,
                nShow=si.wShowWindow
            )
        else:
            os.startfile(path)

        log(f"✅ Opened silently: {path}")

    except Exception as e:
        log(f"❌ Failed to open {path}", e)
        raise


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
