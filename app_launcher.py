import os
import sys
import re
import json
import tkinter as tk
import customtkinter as ctk
from tkinter import filedialog, messagebox
from launcher_logic import run_launch_sequence
import threading
import asyncio
import webbrowser
from ctypes import windll, sizeof, c_int, c_uint, Structure, POINTER, pointer, byref

# ---------- Windows Blur Helper ----------
def enable_acrylic(hwnd):
    """Enable Windows 10/11 acrylic blur + rounded corners."""
    ACCENT_ENABLE_ACRYLICBLURBEHIND = 4
    WCA_ACCENT_POLICY = 19

    class ACCENT_POLICY(Structure):
        _fields_ = [
            ("AccentState", c_int),
            ("AccentFlags", c_int),
            ("GradientColor", c_uint),
            ("AnimationId", c_int),
        ]

    class WINDOW_COMPOSITION_ATTRIB_DATA(Structure):
        _fields_ = [
            ("Attribute", c_int),
            ("Data", POINTER(ACCENT_POLICY)),
            ("SizeOfData", c_int),
        ]

    # Ensure layered window (needed for blur)
    style = windll.user32.GetWindowLongW(hwnd, -20)
    windll.user32.SetWindowLongW(hwnd, -20, style | 0x00080000)  # WS_EX_LAYERED

    # Acrylic blur parameters
    accent = ACCENT_POLICY()
    accent.AccentState = ACCENT_ENABLE_ACRYLICBLURBEHIND
    accent.AccentFlags = 2
    accent.GradientColor = 0x80000000  # semi-transparent black

    data = WINDOW_COMPOSITION_ATTRIB_DATA()
    data.Attribute = WCA_ACCENT_POLICY
    data.Data = pointer(accent)
    data.SizeOfData = sizeof(accent)
    windll.user32.SetWindowCompositionAttribute(hwnd, byref(data))

    # Rounded corners (Windows 11)
    try:
        DWM_WINDOW_CORNER_PREFERENCE = 33
        DWMWCP_ROUND = 2
        windll.dwmapi.DwmSetWindowAttribute(
            hwnd,
            DWM_WINDOW_CORNER_PREFERENCE,
            byref(c_int(DWMWCP_ROUND)),
            sizeof(c_int),
        )
    except Exception:
        pass


# ----- Light/Dark color palette for CTk buttons -----
PALETTE = {
    # primary actions (Add Launch, Open Data Folder)
    "primary": {
        "fg":   ("#2563eb", "#3b82f6"),   # vivid blue (light) / lighter blue (dark)
        "hover":("#1e40af", "#1d4ed8"),
        "text": ("white", "white"),
    },
    # neutral chrome buttons (Settings, Cancel)
    "neutral": {
        "fg":   ("#2563eb", "#3b82f6"),   # very light gray for light mode
        "hover":("#1e40af", "#1d4ed8"),
        "text": ("white", "white"),      # dark text for light mode, white for dark
    },
    # success (Run, Save)
    "success": {
        "fg":   ("#16a34a", "#22c55e"),   # green
        "hover":("#15803d", "#15803d"),
        "text": ("white", "white"),
    },
    # danger (Delete)
    "danger": {
        "fg":   ("#ef4444", "#dc2626"),
        "hover":("#b91c1c", "#b91c1c"),
        "text": ("white", "white"),
    },
    # muted secondary (Edit)
    "muted": {
        "fg":   ("#475569", "#334155"),   # slate gray (darker for light mode)
        "hover":("#334155", "#1f2937"),
        "text": ("white", "white"),
    },
    # file-picker mini button
    "file": {
        "fg":   ("#e2e8f0", "#334155"),
        "hover":("#cbd5e1", "#1f2937"),
        "text": ("#111827", "white"),
    },
}

def themed_border_color():
    import customtkinter as ctk
    dark = ctk.get_appearance_mode().lower() == "dark"
    return None if dark else "#d1d5db"

# ---------------- Paths & Helpers ----------------
def resource_path(relative_path):
    try:
        base_path = sys._MEIPASS  # type: ignore[attr-defined]
    except Exception:
        base_path = os.path.abspath(".")
    return os.path.join(base_path, relative_path)

def get_appdata_dir():
    base = os.path.join(os.getenv("APPDATA"), "App Launcher")
    os.makedirs(base, exist_ok=True)
    return base

DATA_FILE = os.path.join(get_appdata_dir(), "data.json")

def load_bundle():
    try:
        with open(DATA_FILE, "r", encoding="utf-8") as f:
            data = json.load(f)
            if isinstance(data, list):
                # legacy file (only launches)
                return {"launches": data, "settings": {"dark_mode": True, "debug_mode": False}}
            return {
                "launches": data.get("launches", []),
                "settings": {"dark_mode": True, "debug_mode": False} | data.get("settings", {})
            }
    except FileNotFoundError:
        return {"launches": [], "settings": {"dark_mode": True, "debug_mode": False}}

def save_bundle(launches, settings):
    with open(DATA_FILE, "w", encoding="utf-8") as f:
        json.dump({"launches": launches, "settings": settings}, f, indent=2)


class BlurOverlay(ctk.CTkToplevel):
    """Semi-transparent overlay for focus background effect."""

    def __init__(self, master):
        super().__init__(master)
        self.overrideredirect(True)
        self.lift()
        self.transient(master)
        self.attributes("-topmost", True)

        # ✅ Use alpha instead of transparent fg_color
        self.configure(fg_color=("#000000", "#000000"))
        self.attributes("-alpha", 0.25)  # 25% visible, darkened effect

        # Fill entire master window area
        self.geometry(f"{master.winfo_width()}x{master.winfo_height()}+{master.winfo_rootx()}+{master.winfo_rooty()}")

        # Keep it on top of master but behind the settings window
        self.update_idletasks()

    def destroy_overlay(self):
        self.destroy()


# ---------------- Settings Window ----------------
class SettingsWindow(ctk.CTkToplevel):
    def __init__(self, master, appdata_dir, settings, on_save):
        # create overlay first
        self.overlay = BlurOverlay(master)

        # initialize popup
        super().__init__(master)
        self.transient(master)
        self.grab_set()
        self.focus_force()

        self.title("Settings")
        self.geometry("440x380")
        self.resizable(False, False)
        self.appdata_dir = appdata_dir
        self.settings = settings.copy()
        self.on_save = on_save
        self.configure(fg_color=("#f9fafb", "#111827"))
        self._center_to_parent(master, 440, 380)
        self._build_ui()

        # Apply rounded corners
        if sys.platform == "win32":
            hwnd = self.winfo_id()
            DWM_WINDOW_CORNER_PREFERENCE = 33
            DWMWCP_ROUND = 2
            windll.dwmapi.DwmSetWindowAttribute(
                hwnd,
                DWM_WINDOW_CORNER_PREFERENCE,
                byref(c_int(DWMWCP_ROUND)),
                sizeof(c_int),
            )

        # Ensure correct stacking order
        self.lift()           # bring SettingsWindow to front
        self.overlay.lower()  # push blur overlay behind it

        # Close logic
        self.protocol("WM_DELETE_WINDOW", self._close)
        self.bind("<Escape>", lambda e: self._close())

    def _build_ui(self):
        padx = 24
        pady = 16

        header = ctk.CTkLabel(
            self, text="⚙️ Settings", font=ctk.CTkFont(size=22, weight="bold")
        )
        header.pack(pady=(24, 12))

        box = ctk.CTkFrame(self, corner_radius=18, fg_color=("whitesmoke", "#1e293b"))
        box.pack(fill="both", expand=True, padx=padx, pady=(0, 10))

        ctk.CTkButton(
            box,
            text="📂  Open Data Folder",
            command=lambda: webbrowser.open(self.appdata_dir),
            fg_color=("#2563eb", "#3b82f6"),
            hover_color=("#1e40af", "#1d4ed8"),
            text_color="white",
            corner_radius=10,
            height=40,
        ).pack(fill="x", padx=18, pady=(18, 12))

        self._add_switch(box, "🌙 Dark Mode", "dark_mode")
        self._add_switch(box, "🐞 Debug Mode", "debug_mode")

        footer = ctk.CTkFrame(self, fg_color="transparent")
        footer.pack(fill="x", padx=padx, pady=(6, 18))
        btns = ctk.CTkFrame(footer, fg_color="transparent")
        btns.pack(side="right")

        ctk.CTkButton(
            btns,
            text="💾  Save",
            command=self._save,
            fg_color=("#16a34a", "#22c55e"),
            hover_color=("#15803d", "#15803d"),
            text_color="white",
            height=36,
            width=120,
            corner_radius=10,
        ).pack(side="left", padx=8)

        ctk.CTkButton(
            btns,
            text="Cancel",
            command=self._close,
            fg_color=("#475569", "#334155"),
            hover_color=("#334155", "#1f2937"),
            text_color="white",
            height=36,
            width=120,
            corner_radius=10,
        ).pack(side="left")

    def _add_switch(self, parent, label, key):
        """Add a labeled CTkSwitch bound to self.settings[key]."""
        frame = ctk.CTkFrame(parent, fg_color="transparent")
        frame.pack(fill="x", padx=18, pady=6)

        ctk.CTkLabel(
            frame, text=label, font=ctk.CTkFont(size=14)
        ).pack(side="left")

        var = tk.BooleanVar(value=self.settings.get(key, False))
        switch = ctk.CTkSwitch(
            frame,
            text="",
            variable=var,
            onvalue=True,
            offvalue=False,
        )
        switch.pack(side="right")

        # store variable so _save() can access them
        if not hasattr(self, "_switch_vars"):
            self._switch_vars = {}
        self._switch_vars[key] = var


    def _save(self):
        """Save settings to %APPDATA%/App Launcher/config.json and trigger parent callback."""
        # collect toggle values
        if hasattr(self, "_switch_vars"):
            for key, var in self._switch_vars.items():
                self.settings[key] = var.get()

        # write to %APPDATA%/App Launcher/config.json
        try:
            config_path = os.path.join(self.appdata_dir, "config.json")
            with open(config_path, "w", encoding="utf-8") as f:
                json.dump(self.settings, f, indent=2)
        except Exception as e:
            messagebox.showerror("Error", f"Failed to save settings:\n{e}")
            return

        # propagate changes to main app
        if callable(self.on_save):
            self.on_save(self.settings)

        self._close()

    def _center_to_parent(self, master, w, h):
        """Center this window on top of its parent."""
        master.update_idletasks()
        x = master.winfo_rootx() + (master.winfo_width() // 2) - (w // 2)
        y = master.winfo_rooty() + (master.winfo_height() // 2) - (h // 2)
        self.geometry(f"{w}x{h}+{x}+{y}")


    def _close(self):
        try:
            self.overlay.destroy_overlay()
        except Exception:
            pass
        self.destroy()


        
# ---------------- Add/Edit Window ----------------
class LaunchEditor(ctk.CTkToplevel):
    def __init__(self, master, on_save, existing=None):
        super().__init__(master)
        self.title("Add / Edit Launch")
        self.geometry("760x520")
        self.on_save = on_save
        self.paths = existing["paths"][:] if existing else []
        self.name_var = tk.StringVar(value=existing["name"] if existing else "")
        self._build()

    def _build(self):
        self.configure(fg_color=("white", "#0f172a"))
        ctk.CTkLabel(
            self, text="🧩 Add / Edit Launch", font=ctk.CTkFont(size=20, weight="bold")
        ).pack(pady=(16, 6))

        ctk.CTkLabel(self, text="Name", anchor="w").pack(fill="x", padx=20, pady=(6, 0))
        ctk.CTkEntry(self, textvariable=self.name_var, corner_radius=10).pack(fill="x", padx=20, pady=6)

        # Scrollable area with cards for each path
        self.frame_paths = ctk.CTkScrollableFrame(self, fg_color=("white smoke", "#1e293b"), corner_radius=16)
        self.frame_paths.pack(fill="both", expand=True, padx=18, pady=10)

        for p in self.paths:
            self._add_row(p)

        ctk.CTkButton(
            self,
            text="➕ Add Path",
            command=lambda: self._add_row(),
            fg_color=PALETTE["primary"]["fg"],
            hover_color=PALETTE["primary"]["hover"],
            corner_radius=12,
        ).pack(pady=10)

        # Footer
        btns = ctk.CTkFrame(self, fg_color="transparent")
        btns.pack(fill="x", pady=12)
        ctk.CTkButton(
            btns,
            text="💾 Save",
            command=self._save,
            fg_color=PALETTE["success"]["fg"],
            hover_color=PALETTE["success"]["hover"],
            corner_radius=12,
        ).pack(side="left", padx=10)
        ctk.CTkButton(
                        btns,
                        text="Cancel",
                        fg_color=PALETTE["neutral"]["fg"],
                        hover_color=PALETTE["neutral"]["hover"],
                        corner_radius=12,
                        border_width=1,
                        border_color=themed_border_color(),
                        command=self.destroy,
                    ).pack(side="right", padx=10)
        ctk.CTkLabel(self, text="App Launch Name:", anchor="w").pack(fill="x", padx=14, pady=(14, 0))
        ctk.CTkEntry(self, textvariable=self.name_var).pack(fill="x", padx=14, pady=6)

        self.frame_paths = ctk.CTkScrollableFrame(self, fg_color=("white", "#0f172a"))
        self.frame_paths.pack(fill="both", expand=True, padx=12, pady=12)

        for p in self.paths:
            self._add_row(p)

        ctk.CTkButton(self, text="➕ Add Path", command=lambda: self._add_row(),
              fg_color=PALETTE["primary"]["fg"], hover_color=PALETTE["primary"]["hover"]).pack(pady=6)

        btns = ctk.CTkFrame(self, fg_color="transparent")
        btns.pack(fill="x", pady=6)
        ctk.CTkButton(btns, text="💾 Save", command=self._save,
              fg_color=PALETTE["success"]["fg"], hover_color=PALETTE["success"]["hover"]).pack(side="left", padx=10)
        ctk.CTkButton(btns, text="Cancel", fg_color=PALETTE["neutral"]["fg"],
              hover_color=PALETTE["neutral"]["hover"], command=self.destroy).pack(side="right", padx=10)

    def _add_row(self, p=None):
        row = ctk.CTkFrame(self.frame_paths)
        row.pack(fill="x", pady=5, padx=6)
        path_var = tk.StringVar(value=(p["path"] if p else ""))
        delay_var = tk.StringVar(value=str(p["delay"] if p else 0))
        option_var = tk.StringVar(value=(p["start_option"] if p else "Not Maximized"))

        ctk.CTkEntry(row, textvariable=path_var, width=420).pack(side="left", padx=6)
        ctk.CTkButton(row, text="📁", width=34, command=lambda: self._pick(path_var),
              fg_color=PALETTE["file"]["fg"], hover_color=PALETTE["file"]["hover"]).pack(side="left", padx=4)
        ctk.CTkLabel(row, text="Delay").pack(side="left", padx=(8, 4))
        ctk.CTkEntry(row, textvariable=delay_var, width=60).pack(side="left", padx=4)
        ctk.CTkOptionMenu(row, values=["Not Maximized", "Maximized", "Minimized"], variable=option_var).pack(side="left", padx=6)
        ctk.CTkButton(row, text="🗑", width=34,
              fg_color=PALETTE["danger"]["fg"], hover_color=PALETTE["danger"]["hover"],
              command=row.destroy).pack(side="left", padx=6)

        row.path_var = path_var
        row.delay_var = delay_var
        row.option_var = option_var

    def _pick(self, var):
        path = filedialog.askopenfilename(title="Choose Executable",
                                          filetypes=[("Executables", "*.exe *.bat *.cmd *.lnk"), ("All files", "*.*")])
        if path:
            var.set(path)

    def _save(self):
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

# ---------------- Main App ----------------
class AppLauncher(ctk.CTk):
    
    def __init__(self):
        super().__init__()
        self._launching = False

        bundle = load_bundle()
        self.launches = bundle["launches"]
        self.settings = bundle["settings"]

        self.title("Modern App Launcher")
        self.geometry("820x640")

        ctk.set_default_color_theme("dark-blue")
        ctk.set_appearance_mode("dark" if self.settings.get("dark_mode", True) else "light")

        self._build_ui()
        self._init_log_tags()

    # ---------- Theme & Animation ----------
    def animate_theme_switch(self, mode: str):
        # quick fade animation using window alpha
        try:
            for a in (0.97, 0.94, 0.91, 0.88):
                self.attributes("-alpha", a)
                self.update_idletasks()
                self.after(12)
            ctk.set_appearance_mode(mode)
            for a in (0.91, 0.94, 0.97, 1.0):
                self.attributes("-alpha", a)
                self.update_idletasks()
                self.after(12)
        except Exception:
            # fallback without animation
            ctk.set_appearance_mode(mode)
            self.attributes("-alpha", 1.0)

        # refresh tag colors after theme change
        self._init_log_tags()

    # ---------- UI ----------
    def _build_ui(self):
        # Top bar
        top = ctk.CTkFrame(self, corner_radius=18)
        top.pack(fill="x", padx=12, pady=12)

        ctk.CTkLabel(
            top,
            text="App Launches",
            font=ctk.CTkFont(size=22, weight="bold")
        ).pack(side="left", padx=14, pady=10)

        # ⚙️ Settings button
        ctk.CTkButton(
            top,
            text="⚙️  Settings",
            width=130,  # 🔹 Match Add Launch
            command=self.open_settings,
            fg_color=PALETTE["neutral"]["fg"],
            hover_color=PALETTE["neutral"]["hover"]
        ).pack(side="right", padx=8, pady=10)

        # ➕ Add Launch button
        ctk.CTkButton(
            top,
            text="➕  Add Launch",
            width=130,  # 🔹 Same width
            command=self.add_launch,
            fg_color=PALETTE["primary"]["fg"],
            hover_color=PALETTE["primary"]["hover"]
        ).pack(side="right", padx=8, pady=10)

        # Content area
        self.list_frame = ctk.CTkScrollableFrame(self, corner_radius=16)
        self.list_frame.pack(fill="both", expand=True, padx=12, pady=(0, 10))

        # Log box
        log_wrap = ctk.CTkFrame(self, corner_radius=16)
        log_wrap.pack(fill="x", padx=12, pady=(0, 12))
        ctk.CTkLabel(log_wrap, text="Log", font=ctk.CTkFont(size=14, weight="bold")).pack(anchor="w", padx=12, pady=(8, 0))

        self.log_box = ctk.CTkTextbox(log_wrap, height=140, corner_radius=12)
        self.log_box.pack(fill="x", padx=10, pady=10)

        self.refresh_list()

    def _init_log_tags(self):
        # Colors per theme
        dark = ctk.get_appearance_mode().lower() == "dark"

        info_color = "#ffffff" if dark else "#0b0f1a"  # white for dark, near-black for light (readable)
        debug_color = "#ff9800"                        # orange
        error_color = "#ef4444"                        # red
        path_user_color = "#3b82f6"                    # blue
        path_debug_color = "#c2410c"                   # dark orange

        # configure tags
        self.log_box.tag_config("INFO", foreground=info_color)
        self.log_box.tag_config("DEBUG", foreground=debug_color)
        self.log_box.tag_config("ERROR", foreground=error_color)
        self.log_box.tag_config("PATH_USER", foreground=path_user_color)
        self.log_box.tag_config("PATH_DEBUG", foreground=path_debug_color)

    # ---------- Settings ----------
    def open_settings(self):
        config_path = os.path.join(get_appdata_dir(), "config.json")
        if os.path.exists(config_path):
            try:
                with open(config_path, "r", encoding="utf-8") as f:
                    self.settings.update(json.load(f))
            except Exception:
                pass

        def on_save(new_settings):
            old_mode = "dark" if self.settings.get("dark_mode", True) else "light"
            self.settings = new_settings
            save_bundle(self.launches, self.settings)
            new_mode = "dark" if self.settings.get("dark_mode", True) else "light"
            if new_mode != old_mode:
                self.animate_theme_switch(new_mode)

        SettingsWindow(self, get_appdata_dir(), self.settings, on_save)

    # ---------- List / Cards ----------
    def refresh_list(self):
        for w in self.list_frame.winfo_children():
            w.destroy()
        for i, launch in enumerate(self.launches):
            self._card(launch, i)

    def _card(self, launch, index):
        card = ctk.CTkFrame(
                    self.list_frame,
                    corner_radius=16,
                    fg_color=("white smoke", "#1e293b"),  # Light gray vs dark navy-gray
                )

        card.pack(fill="x", pady=6, padx=10)

        left = ctk.CTkFrame(card, fg_color="transparent")
        left.pack(side="left", fill="x", expand=True)
        ctk.CTkLabel(left, text=launch["name"], font=ctk.CTkFont(size=16, weight="bold")).pack(anchor="w", padx=12, pady=(10, 0))
        ctk.CTkLabel(left, text=f"{len(launch['paths'])} app(s)", text_color=("gray20", "gray70")).pack(anchor="w", padx=12, pady=(0, 10))

        ctk.CTkButton(card, text="▶️ Run", width=70, command=lambda l=launch: self.run_launch(l),
              fg_color=PALETTE["success"]["fg"], hover_color=PALETTE["success"]["hover"]).pack(side="right", padx=8, pady=12)
        ctk.CTkButton(
                        card,
                        text="✏️ Edit",
                        width=70,
                        command=lambda i=index: self.edit_launch(i),
                        fg_color=PALETTE["muted"]["fg"],
                        hover_color=PALETTE["muted"]["hover"],
                        border_width=1,
                        border_color=themed_border_color(),
                    ).pack(side="right", padx=8, pady=12)
        ctk.CTkButton(card, text="🗑️ Del", width=70, command=lambda i=index: self.delete_launch(i),
              fg_color=PALETTE["danger"]["fg"], hover_color=PALETTE["danger"]["hover"]).pack(side="right", padx=8, pady=12)

    def add_launch(self):
        LaunchEditor(self, on_save=self._on_added)

    def _on_added(self, data):
        self.launches.append(data)
        save_bundle(self.launches, self.settings)
        self.refresh_list()

    def edit_launch(self, index):
        LaunchEditor(self, on_save=lambda d: self._on_edited(index, d), existing=self.launches[index])

    def _on_edited(self, index, data):
        self.launches[index] = data
        save_bundle(self.launches, self.settings)
        self.refresh_list()

    def delete_launch(self, index):
        if messagebox.askyesno("Confirm", f"Delete '{self.launches[index]['name']}'?"):
            self.launches.pop(index)
            save_bundle(self.launches, self.settings)
            self.refresh_list()

    # ---------- Logging with Colors ----------
    _PATH_QUOTED = re.compile(r'"([A-Za-z]:\\[^"]+)"')
    _PATH_BARE   = re.compile(r'([A-Za-z]:\\[^\s]+(?:\s[^\s]+)*)')

    def _insert_colored_line(self, text, tag="INFO"):
        """
        Insert a line with color tags; paths inside are colored depending on debug mode.
        """
        # Choose path color tag based on debug toggle
        path_tag = "PATH_DEBUG" if self.settings.get("debug_mode", False) else "PATH_USER"

        # Insert base line start index
        start_index = self.log_box.index("end-1c")

        # Insert plain first, then tag ranges
        self.log_box.insert("end", text)

        # Find quoted paths first
        for m in self._PATH_QUOTED.finditer(text):
            s = f"{start_index}+{m.start(1)}c"
            e = f"{start_index}+{m.end(1)}c"
            self.log_box.tag_add(path_tag, s, e)

        # Then bare paths (that aren't already quoted ranges)
        for m in self._PATH_BARE.finditer(text):
            # skip if this span overlaps a quoted match
            if text[max(0, m.start()-1):m.start()] == '"' or text[m.end():m.end()+1] == '"':
                continue
            s = f"{start_index}+{m.start(1)}c"
            e = f"{start_index}+{m.end(1)}c"
            self.log_box.tag_add(path_tag, s, e)

        # Apply the main line tag last so it doesn't override path tag colors
        self.log_box.tag_add(tag, start_index, f"{start_index}+{len(text)}c")

    def log(self, text, end="\n"):
        """
        Color rules:
          INFO  (default): white(dark)/near-black(light)
          DEBUG: orange
          ERROR: red
          Paths inside a line: blue (debug off) / dark orange (debug on)
        Countdown uses end="\r" to overwrite same line without spamming.
        """
        # determine top-level tag from content prefix
        tag = "INFO"
        if text.startswith("[DEBUG]"):
            tag = "DEBUG"
        elif text.startswith("❌") or text.startswith("[ERROR]"):
            tag = "ERROR"

        if end == "\r":
            # Overwrite only the current last line (do not wipe previous lines)
            try:
                self.log_box.delete("end-1l linestart", "end-1c")
            except Exception:
                pass
            self._insert_colored_line(text, tag)
        else:
            self._insert_colored_line(text + end, tag)

        self.log_box.see("end")
        self.update_idletasks()

    # ---------- Run ----------
    def run_launch(self, launch):
        if getattr(self, "_launching", False):
            self.log("[DEBUG] Launch aborted: already running.")
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
            self.log(f"❌ Error: {e}")
        finally:
            self._launching = False

if __name__ == "__main__":
    app = AppLauncher()
    app.mainloop()
