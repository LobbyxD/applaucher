import asyncio
import subprocess
import win32con
import win32process
import psutil
import os

async def launch_app(path: str, delay: float, start_option: str):
    """Launch an app or batch file with correct visibility behavior."""
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

    exe_name = os.path.basename(path).lower()
    if exe_name.endswith(".exe"):
        exe_name = exe_name  # e.g., Ryujinx.exe
    elif exe_name.endswith(".bat"):
        exe_name = exe_name[:-4] + ".exe"  # guess main exe name if same base

    # ✅ Check if already running
    for p in psutil.process_iter(attrs=["name"]):
        try:
            if p.info["name"] and p.info["name"].lower() == exe_name:
                print(f"⚠️ {exe_name} is already running. Skipping.")
                return
        except psutil.NoSuchProcess:
            continue

    # ✅ Detect .bat files and use cmd /c to run them silently
    if path.lower().endswith(".bat"):
        subprocess.Popen(["cmd.exe", "/c", path], startupinfo=si, creationflags=creation_flags)
    else:
        subprocess.Popen([path], startupinfo=si, creationflags=creation_flags)

    await asyncio.sleep(delay)


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
    for idx, app in enumerate(apps, start=1):
        path = app["path"]
        delay = float(app["delay"])
        opt = app["start_option"]

        # --- Log launch ---
        if progress_cb:
            progress_cb(f"Launching {idx}/{total}: {path} ({opt})...")

        try:
            await launch_app(path, 0, opt)
        except Exception as e:
            if progress_cb:
                progress_cb(f"❌ Error launching {path}: {e}")
            continue

        # --- Countdown between apps ---
        if idx < total and delay > 0:
            for remaining in range(int(delay), 0, -1):
                if progress_cb:
                    # overwrite same line (no newline)
                    progress_cb(f"⏳ Waiting {remaining:>2}s before next...", end="\r")
                await asyncio.sleep(1)

            # Clear line once countdown finishes
            if progress_cb:
                progress_cb(" " * 60, end="\r")

    if progress_cb:
        progress_cb("✅ Done.")