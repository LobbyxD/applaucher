# === build.py (Steam-ready, fully self-cleaning version) ===
import json
import os
import shutil
import subprocess
import sys
import export_folder_hierarchy

def export_project_tree():
    """
    Export the folder hierarchy of the current project
    into the same folder build.py lives in.
    """
    project_root = os.getcwd()
    export_folder_hierarchy.export_hierarchy(project_root)


# ----------------- Load config -----------------
with open("app_settings.json", "r", encoding="utf-8") as f:
    cfg = json.load(f)

EXE_NAME = cfg["exe_name"]            # "AppLauncher"
ICON_PATH = cfg["icon_path"]          # "resources/icons/AppLauncher.ico"
INCLUDE_RES = cfg["include_resources"]  # "resources/icons;resources/icons"
VERSION = cfg.get("version", "0.0.0")

DIST_DIR = "dist"
BUILD_DIR = "build"
RELEASE_DIR = "release"

# ----------------- Command helpers -----------------
def run(cmd):
    print(">", " ".join(cmd))
    subprocess.run(cmd, check=True)

def ensure_dir(path):
    os.makedirs(path, exist_ok=True)

def safe_rmtree(path):
    if os.path.exists(path):
        shutil.rmtree(path, ignore_errors=True)

def safe_remove(path):
    if os.path.exists(path):
        try:
            os.remove(path)
        except Exception:
            pass

# ----------------- Build process -----------------
def build():
    """Compile the PyQt app into a single .exe"""
    print(f"🚀 Building {EXE_NAME}.exe …")

    # Clean temp dirs first for a fully fresh build
    safe_rmtree(DIST_DIR)
    safe_rmtree(BUILD_DIR)

    pyi_cmd = [
        sys.executable, "-m", "PyInstaller",
        "--onefile",
        "--noconsole",
        "--clean",
        f"--icon={ICON_PATH}",
        f"--add-data={INCLUDE_RES}",
        "--add-data=app_settings.json;.",
        f"--name={EXE_NAME}",
        "main.py",
    ]

    run(pyi_cmd)

    exe_src = os.path.join(DIST_DIR, f"{EXE_NAME}.exe")
    if not os.path.exists(exe_src):
        raise FileNotFoundError(f"❌ Expected built exe not found: {exe_src}")

    # Delete the automatically generated spec file — not needed
    safe_remove(f"{EXE_NAME}.spec")

    print("✅ PyInstaller build OK (spec file deleted).")

# ----------------- Optional: Code signing -----------------
def sign_exe_if_available():
    """Optional: sign exe if signtool.exe exists (skips silently otherwise)."""
    exe_path = os.path.join(DIST_DIR, f"{EXE_NAME}.exe")
    signtool_path = r"C:\Program Files (x86)\Windows Kits\10\bin\10.0.26100.0\x64\signtool.exe"
    if not os.path.exists(signtool_path):
        print("ℹ️ signtool.exe not found — skipping code signing.")
        return

    try:
        print(f"🔏 Signing {exe_path} …")
        run([
            signtool_path,
            "sign",
            "/tr", "http://timestamp.sectigo.com",
            "/td", "sha256",
            "/fd", "sha256",
            "/a",
            exe_path,
        ])
        print("✅ Code signing OK.")
    except subprocess.CalledProcessError as e:
        print(f"⚠️ Code signing failed: {e}")

# ----------------- Release preparation -----------------
def prepare_release():
    """Copy only the required runtime assets into ./release for Steam."""
    print("📦 Preparing clean release folder …")

    # Full cleanup of /release before copying
    safe_rmtree(RELEASE_DIR)
    ensure_dir(RELEASE_DIR)

    # Copy built exe
    exe_src = os.path.join(DIST_DIR, f"{EXE_NAME}.exe")
    shutil.copy(exe_src, os.path.join(RELEASE_DIR, f"{EXE_NAME}.exe"))

    # Copy necessary top-level files
    for fname in ["app_settings.json", "LICENSE", "README.md"]:
        if os.path.exists(fname):
            shutil.copy(fname, os.path.join(RELEASE_DIR, fname))
        else:
            print(f"⚠️ {fname} not found — skipping.")

    # Copy resources (icons, etc.)
    if os.path.exists("resources"):
        shutil.copytree("resources", os.path.join(RELEASE_DIR, "resources"), dirs_exist_ok=True)
    else:
        print("⚠️ resources/ folder missing — UI icons will not load.")

    # Add version marker
    with open(os.path.join(RELEASE_DIR, "version.txt"), "w", encoding="utf-8") as vf:
        vf.write(f"{VERSION}\n")

    print("✅ Release folder ready at ./release/")

# ----------------- Cleanup extras -----------------
def cleanup_misc():
    """Delete unnecessary leftovers and duplicate .spec files."""
    print("🧹 Cleaning up unnecessary files …")

    # Delete PyInstaller temp build dirs
    safe_rmtree(BUILD_DIR)

    # Delete any remaining .spec files
    for file in os.listdir("."):
        if file.endswith(".spec"):
            safe_remove(file)
            print(f"   🗑 Deleted {file}")

    print("🧽 Cleanup complete.")

# ----------------- Entry point -----------------
if __name__ == "__main__":
    export_project_tree()
    build()
    sign_exe_if_available()
    prepare_release()
    cleanup_misc()
    print("\n🎉 Build complete. Upload ./release to Steam.")
