import os
import sys
import json
import tkinter as tk
import customtkinter as ctk
from tkinter import filedialog, messagebox
from launcher_logic import run_launch_sequence
import threading
import asyncio
import webbrowser

# ---------- Helper Functions ----------
def resource_path(relative_path):
    """Get absolute path to resource, works for dev and PyInstaller build."""
    try:
        base_path = sys._MEIPASS
    except Exception:
        base_path = os.path.abspath(".")
    return os.path.join(base_path, relative_path)


def get_appdata_dir():
    """Return %APPDATA%\App Launcher and create it if missing."""
    base = os.path.join(os.getenv("APPDATA"), "App Launcher")
    os.makedirs(base, exist_ok=True)
    return base


DATA_FILE = os.path.join(get_appdata_dir(), "data.json")


def load_launches():
    try:
        with open(DATA_FILE, "r", encoding="utf-8") as f:
            data = json.load(f)
            return data if isinstance(data, list) else data.get("launches", [])
    except FileNotFoundError:
        return []


def load_settings():
    try:
        with open(DATA_FILE, "r", encoding="utf-8") as f:
            data = json.load(f)
            if isinstance(data, dict) and "settings" in data:
                return data["settings"]
    except FileNotFoundError:
        pass
    return {"dark_mode": True, "debug_mode": False}


def save_data(launches, settings):
    with open(DATA_FILE, "w", encoding="utf-8") as f:
        json.dump({"launches": launches, "settings": settings}, f, indent=2)


# ---------- Settings Window ----------
class SettingsWindow(ctk.CTkToplevel):
    def __init__(self, master, appdata_dir, settings, on_save):
        super().__init__(master)
        self.title("Settings")
        self.geometry("400x300")
        self.appdata_dir = appdata_dir
        self.settings = settings.copy()
        self.on_save = on_save
        self.build_ui()

    def build_ui(self):
        ctk.CTkLabel(self, text="Settings", font=ctk.CTkFont(size=20, weight="bold")).pack(pady=(15, 10))

        # Open folder button
        ctk.CTkButton(self, text="📂 Open Data Folder", command=self.open_data_folder).pack(pady=10)

        # Dark mode toggle
        frame1 = ctk.CTkFrame(self)
        frame1.pack(fill="x", padx=20, pady=10)
        ctk.CTkLabel(frame1, text="Dark Mode").pack(side="left", padx=10)
        self.dark_toggle = ctk.CTkSwitch(frame1, text="", onvalue=True, offvalue=False)
        self.dark_toggle.pack(side="right", padx=10)
        self.dark_toggle.select() if self.settings.get("dark_mode", True) else self.dark_toggle.deselect()

        # Debug mode toggle
        frame2 = ctk.CTkFrame(self)
        frame2.pack(fill="x", padx=20, pady=10)
        ctk.CTkLabel(frame2, text="Debug Mode").pack(side="left", padx=10)
        self.debug_toggle = ctk.CTkSwitch(frame2, text="", onvalue=True, offvalue=False)
        self.debug_toggle.pack(side="right", padx=10)
        self.debug_toggle.select() if self.settings.get("debug_mode", False) else self.debug_toggle.deselect()

        # Buttons
        btns = ctk.CTkFrame(self)
        btns.pack(fill="x", pady=20)
        ctk.CTkButton(btns, text="Save", command=self.save).pack(side="left", padx=15)
        ctk.CTkButton(btns, text="Cancel", fg_color="gray", command=self.destroy).pack(side="right", padx=15)

    def open_data_folder(self):
        webbrowser.open(self.appdata_dir)

    def save(self):
        self.settings["dark_mode"] = bool(self.dark_toggle.get())
        self.settings["debug_mode"] = bool(self.debug_toggle.get())
        self.on_save(self.settings)
        self.destroy()


# ---------- Add/Edit Window ----------
class LaunchEditor(ctk.CTkToplevel):
    def __init__(self, master, on_save, existing=None):
        super().__init__(master)
        self.title("Add / Edit Launch")
        self.geometry("700x500")
        self.on_save = on_save
        self.paths = existing["paths"][:] if existing else []
        self.name_var = tk.StringVar(value=existing["name"] if existing else "")
        self.build_ui()

    def build_ui(self):
        ctk.CTkLabel(self, text="App Launch Name:", anchor="w").pack(fill="x", padx=10, pady=(10, 0))
        ctk.CTkEntry(self, textvariable=self.name_var).pack(fill="x", padx=10, pady=5)

        self.frame_paths = ctk.CTkScrollableFrame(self)
        self.frame_paths.pack(fill="both", expand=True, padx=10, pady=10)

        for p in self.paths:
            self._add_path_row(p)
        ctk.CTkButton(self, text="➕ Add Path", command=lambda: self._add_path_row()).pack(pady=4)

        btns = ctk.CTkFrame(self)
        btns.pack(fill="x", pady=6)
        ctk.CTkButton(btns, text="💾 Save", command=self.save).pack(side="left", padx=10)
        ctk.CTkButton(btns, text="Cancel", fg_color="gray", command=self.destroy).pack(side="right", padx=10)

    def _add_path_row(self, p=None):
        row = ctk.CTkFrame(self.frame_paths)
        row.pack(fill="x", pady=4, padx=5)
        path_var = tk.StringVar(value=p["path"] if p else "")
        delay_var = tk.StringVar(value=str(p["delay"] if p else 0))
        option_var = tk.StringVar(value=p["start_option"] if p else "Not Maximized")

        ctk.CTkEntry(row, textvariable=path_var, width=360).pack(side="left", padx=5)
        ctk.CTkButton(row, text="📁", width=30, command=lambda: self._choose_file(path_var)).pack(side="left", padx=3)
        ctk.CTkLabel(row, text="Delay:").pack(side="left")
        ctk.CTkEntry(row, textvariable=delay_var, width=50).pack(side="left", padx=5)
        ctk.CTkOptionMenu(row, values=["Not Maximized", "Maximized", "Minimized"], variable=option_var).pack(side="left", padx=5)
        ctk.CTkButton(row, text="🗑", width=30, fg_color="red", command=row.destroy).pack(side="left", padx=5)

        row.path_var = path_var
        row.delay_var = delay_var
        row.option_var = option_var

    def _choose_file(self, var):
        path = filedialog.askopenfilename(title="Choose Executable", filetypes=[("EXE Files", "*.exe"), ("All", "*.*")])
        if path:
            var.set(path)

    def save(self):
        name = self.name_var.get().strip() or "Untitled"
        apps = []
        for child in self.frame_paths.winfo_children():
            p = child.path_var.get().strip()
            if not p:
                continue
            try:
                delay = float(child.delay_var.get() or 0)
            except ValueError:
                delay = 0
            apps.append({"path": p, "delay": delay, "start_option": child.option_var.get()})
        if not apps:
            messagebox.showwarning("Empty", "Please add at least one path.")
            return
        self.on_save({"name": name, "paths": apps})
        self.destroy()


# ---------- Main App ----------
class AppLauncher(ctk.CTk):
    def __init__(self):
        super().__init__()
        self._launching = False
        self.settings = load_settings()
        self.title("Modern App Launcher")
        self.geometry("700x600")

        # Set theme
        ctk.set_default_color_theme("dark-blue")
        ctk.set_appearance_mode("dark" if self.settings.get("dark_mode", True) else "light")

        self.launches = load_launches()
        self.loop = asyncio.new_event_loop()
        self.build_ui()

    def build_ui(self):
        top = ctk.CTkFrame(self)
        top.pack(fill="x", pady=10)
        ctk.CTkLabel(top, text="App Launches", font=ctk.CTkFont(size=20, weight="bold")).pack(side="left", padx=10)

        ctk.CTkButton(top, text="⚙️ Settings", width=100, command=self.open_settings).pack(side="right", padx=10)
        ctk.CTkButton(top, text="➕ Add Launch", width=120, command=self.add_launch).pack(side="right", padx=10)

        self.list_frame = ctk.CTkScrollableFrame(self)
        self.list_frame.pack(fill="both", expand=True, padx=10, pady=10)

        self.log_box = ctk.CTkTextbox(self, height=100)
        self.log_box.pack(fill="x", padx=10, pady=(0, 10))
        self.refresh_list()

    def open_settings(self):
        SettingsWindow(self, get_appdata_dir(), self.settings, self._on_settings_saved)

    def _on_settings_saved(self, new_settings):
        self.settings = new_settings
        save_data(self.launches, self.settings)
        # Update theme live
        ctk.set_appearance_mode("dark" if self.settings.get("dark_mode", True) else "light")

    def refresh_list(self):
        for child in self.list_frame.winfo_children():
            child.destroy()
        for i, launch in enumerate(self.launches):
            self._add_launch_card(launch, i)

    def _add_launch_card(self, launch, index):
        card = ctk.CTkFrame(self.list_frame)
        card.pack(fill="x", pady=5, padx=5)
        ctk.CTkLabel(card, text=launch["name"], font=ctk.CTkFont(size=16, weight="bold")).pack(side="left", padx=10)
        ctk.CTkLabel(card, text=f"{len(launch['paths'])} app(s)", text_color="gray").pack(side="left")
        ctk.CTkButton(card, text="▶️ Run", width=60, command=lambda l=launch: self.run_launch(l)).pack(side="right", padx=5)
        ctk.CTkButton(card, text="✏️ Edit", width=60, command=lambda i=index: self.edit_launch(i)).pack(side="right", padx=5)
        ctk.CTkButton(card, text="🗑️ Del", width=60, fg_color="red", command=lambda i=index: self.delete_launch(i)).pack(side="right", padx=5)

    def add_launch(self):
        LaunchEditor(self, on_save=self._on_added)

    def _on_added(self, data):
        self.launches.append(data)
        save_data(self.launches, self.settings)
        self.refresh_list()

    def edit_launch(self, index):
        LaunchEditor(self, on_save=lambda d: self._on_edited(index, d), existing=self.launches[index])

    def _on_edited(self, index, data):
        self.launches[index] = data
        save_data(self.launches, self.settings)
        self.refresh_list()

    def delete_launch(self, index):
        if messagebox.askyesno("Confirm", f"Delete '{self.launches[index]['name']}'?"):
            self.launches.pop(index)
            save_data(self.launches, self.settings)
            self.refresh_list()

    def log(self, text, end="\n"):
        if end == "\r":
            self.log_box.delete("end-1l linestart", "end-1c")
            self.log_box.insert("end", text)
        else:
            self.log_box.insert("end", text + end)
        self.log_box.see("end")
        self.update_idletasks()

    def run_launch(self, launch):
        if getattr(self, "_launching", False):
            self.log("⚠️ A launch is already running.")
            return
        self._launching = True
        self.log(f"▶️ Starting {launch['name']}...")
        t = threading.Thread(target=self._run_launch_in_thread, args=(launch,), daemon=True)
        t.start()

    def _run_launch_in_thread(self, launch):
        async def run():
            await run_launch_sequence(launch["paths"], self.log)
        try:
            asyncio.run(run())
        except Exception as e:
            self.log(f"💥 Error: {e}")
        finally:
            self._launching = False


if __name__ == "__main__":
    app = AppLauncher()
    app.mainloop()
