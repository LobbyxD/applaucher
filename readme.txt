build/dist clear: Remove-Item -Recurse -Force build, dist
.exe Creation: pyinstaller --onefile --noconsole --icon=AppLauncher.ico app_launcher.py --add-data "AppLauncher.ico;."