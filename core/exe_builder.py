import os, json, subprocess
from PyQt6.QtCore import QStandardPaths

def build_single_launcher(name: str, bundle: dict):
    """Builds a standalone .exe launcher for a single App Launch entry."""
    base_dir = QStandardPaths.writableLocation(QStandardPaths.StandardLocation.AppDataLocation)
    custom_dir = os.path.join(base_dir, "custom_launchers")
    os.makedirs(custom_dir, exist_ok=True)

    # Step 1: Write mini runner script
    script_path = os.path.join(custom_dir, f"{name}_runner.py")
    script_content = f'''import asyncio, subprocess, os, win32con, win32process

async def launch_app(path: str, delay: float, start_option: str):
    path = path.strip().strip('"').strip("'")
    si = subprocess.STARTUPINFO()
    si.dwFlags |= win32con.STARTF_USESHOWWINDOW

    if start_option == "Maximized":
        si.wShowWindow = win32con.SW_SHOWMAXIMIZED
    elif start_option == "Minimized":
        si.wShowWindow = win32con.SW_SHOWMINNOACTIVE
    else:
        si.wShowWindow = win32con.SW_SHOWNORMAL

    creation_flags = win32process.DETACHED_PROCESS if start_option == "Minimized" else 0

    if path.lower().endswith(".bat"):
        subprocess.Popen(["cmd.exe", "/c", path], startupinfo=si, creationflags=creation_flags)
    else:
        subprocess.Popen([path], startupinfo=si, creationflags=creation_flags)

async def run_launch_sequence(apps):
    total = len(apps)
    for idx, app in enumerate(apps, start=1):
        try:
            await launch_app(app["path"], 0, app["start_option"])
        except Exception as e:
            print(f"Error launching {{app['path']}}: {{e}}")
            continue
        if idx < total and app["delay"] > 0:
            await asyncio.sleep(app["delay"])
    print("✅ Done.")

bundle = {json.dumps(bundle, indent=2)}
asyncio.run(run_launch_sequence(bundle["paths"]))
'''

    with open(script_path, "w", encoding="utf-8") as f:
        f.write(script_content)

    # Step 2: Build .exe with PyInstaller
    # ✅ Use QStandardPaths instead of winshell to find Desktop
    desktop = QStandardPaths.writableLocation(QStandardPaths.StandardLocation.DesktopLocation)
    if not desktop or not os.path.exists(desktop):
        desktop = os.path.join(os.path.expanduser("~"), "Desktop")

    exe_name = f"{name} Launcher"
    exe_path = os.path.join(desktop, exe_name + ".exe")

    icon_path = os.path.join(os.path.dirname(__file__), "..", "resources", "icons", "AppLauncher.ico")

    cmd = [
        "pyinstaller",
        "--onefile",
        "--noconsole",
        f"--icon={icon_path}",
        f"--name={exe_name}",
        script_path
    ]
    subprocess.run(cmd, shell=True, check=True)

    # Step 3: Detect where PyInstaller output actually is
    dist_dir = os.path.join(os.getcwd(), "dist")
    exe_filename = f"{exe_name}.exe"

    dist_exe = os.path.join(dist_dir, exe_filename)
    if not os.path.exists(dist_exe):
        alt_exe = os.path.join(dist_dir, exe_name, exe_filename)
        if os.path.exists(alt_exe):
            dist_exe = alt_exe
        else:
            raise FileNotFoundError(f"PyInstaller output not found in {dist_dir}")

    # Step 4: Move result to Desktop
    os.makedirs(desktop, exist_ok=True)
    os.replace(dist_exe, exe_path)

    # Step 5: Cleanup build artifacts
    for folder in ("build", "dist", f"{exe_name}.spec"):
        if os.path.exists(folder):
            try:
                if os.path.isdir(folder):
                    import shutil
                    shutil.rmtree(folder)
                else:
                    os.remove(folder)
            except Exception:
                pass

    return exe_path
