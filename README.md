```markdown
# 🚀 App Launcher

A modern **Python + PyQt6 desktop application** that lets you create and manage custom launch profiles to open multiple programs or scripts with optional delays and start modes.

---

## 🖥️ Features

- 🧩 Create named launch profiles
- ⚙️ Add multiple executables per profile
- ⏱️ Set launch delays and start modes (Normal / Minimized / Maximized)
- 💾 Saves settings in your AppData folder (`%AppData%/App Launcher`)
- 🎨 Light / Dark theme toggle (auto-saved)
- 📁 Fully self-contained build — no installer required

---

## 📦 Project Structure
```

App Launcher/
├── main.py # Application entry point
├── build.py # Build helper script
├── make_icon.py # Converts PNG → ICO for the app icon
├── app_settings.json # Build metadata (name, icon, resources)
├── core/ # Logic layer: storage, launcher logic, app settings
├── ui/ # PyQt6 UI: main window, dialogs, widgets
├── resources/ # Icons and assets
└── README.md

````

---

## 🧰 Requirements

- **Python 3.10+** (tested on 3.14)
- **PyQt6**
- **pyinstaller**
- **pillow**
- **psutil**
- **pywin32**

Install all dependencies:
```bash
pip install -r requirements.txt
````

If you don’t have a `requirements.txt`, you can create one easily:

```bash
pip freeze > requirements.txt
```

---

## 🏗️ Build Instructions

There are two supported build methods:

### 🧱 Option 1: Use the automated builder (`build.py`)

> Recommended – keeps configuration in `app_settings.json`

```bash
python build.py
```

This reads:

```json
{
  "app_name": "App Launcher",
  "exe_name": "AppLauncher",
  "window_title": "App Launcher",
  "version": "1.0.0",
  "icon_path": "resources/icons/AppLauncher.ico",
  "include_resources": "resources/icons;resources/icons"
}
```

and generates a standalone `.exe` inside the `dist/` folder.

---

### ⚙️ Option 2: Manual PyInstaller command

If you prefer to build manually, use:

```bash
pyinstaller --onefile --noconsole ^
  --name "AppLauncher" ^
  --icon "resources/icons/AppLauncher.ico" ^
  --add-data "resources/icons;resources/icons" ^
  --add-data "app_settings.json;." ^
  main.py
```

The output executable will appear in:

```
dist/AppLauncher.exe
```

---

## 🧹 Cleaning the build

To remove previous build artifacts:

```bash
Remove-Item -Recurse -Force build, dist
```

(Or use `rm -rf build dist` on macOS/Linux.)

---

## 🪟 Running Locally (Dev Mode)

Simply run:

```bash
python main.py
```

The app will launch with your local Python environment and automatically use your system’s `%AppData%` path for settings and launch data.

---

## 📁 AppData storage locations

| Type                  | Location                               | Description              |
| --------------------- | -------------------------------------- | ------------------------ |
| Launch configurations | `%AppData%/App Launcher/launches.json` | Saved user launcher data |
| Theme settings        | `%AppData%/App Launcher/settings.json` | Dark/Light mode          |

These are automatically created — no manual setup required.

---

## 🧩 License

This project is distributed under the MIT License.
See [`LICENSE`](LICENSE) for details.

---

## 👨‍💻 Author

Developed by **Daniel Shafir**
🪄 Built with ❤️ using Python + PyQt6

```

```
