# build.py
import json
import os
import subprocess

with open("app_settings.json", "r", encoding="utf-8") as f:
    cfg = json.load(f)

# --- build command ---
cmd = (
    f'pyinstaller --onefile --noconsole '
    f'--icon={cfg["icon_path"]} '
    f'--add-data "{cfg["include_resources"]}" '
    f'--add-data "app_settings.json;." '  # ✅ include settings file
    f'--name "{cfg["exe_name"]}" '
    'main.py'
)

print(f"🚀 Building: {cfg['exe_name']}.exe")
os.system(cmd)
