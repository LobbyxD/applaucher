# build.py
import json
import os
import subprocess

with open("app_settings.json", "r", encoding="utf-8") as f:
    cfg = json.load(f)
    cmd1 = f'pyinstaller --onefile'
    cmd2 = f'pyinstaller --onefile --noconsole '

# --- build command ---
cmd = (
    f'{cmd2} '
    f'--icon={cfg["icon_path"]} '
    f'--add-data "{cfg["include_resources"]}" '
    f'--add-data "app_settings.json;." '
    f'--name "{cfg["exe_name"]}" '
    'main.py'
)

print(f"🚀 Building: {cfg['exe_name']}.exe")
os.system(cmd)
