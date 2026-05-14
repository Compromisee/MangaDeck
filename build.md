
---

## Building to Executable

Mangadeck can be compiled into a standalone executable that requires no Python installation on the target machine. The executable bundles all dependencies, templates, and static files.

### Prerequisites

Install PyInstaller into your environment:

```bash
pip install pyinstaller
```

---

### Windows — `.exe`

#### Quick build (one command)

```bash
pyinstaller --noconfirm --onefile --windowed ^
  --name "Mangadeck" ^
  --icon "docs/assets/icon.ico" ^
  --add-data "web/templates;web/templates" ^
  --add-data "web/static;web/static" ^
  --hidden-import "flask" ^
  --hidden-import "bs4" ^
  --hidden-import "PIL" ^
  --hidden-import "rich" ^
  --hidden-import "pyfiglet" ^
  --hidden-import "requests" ^
  main.py
```

The executable is created at `dist/Mangadeck.exe`.

#### Using the spec file (recommended for reproducible builds)

Create `mangadeck.spec` in the repo root:

```python
# mangadeck.spec
import sys
import os
from PyInstaller.utils.hooks import collect_data_files, collect_submodules

block_cipher = None

added_files = [
    ("web/templates", "web/templates"),
    ("web/static",    "web/static"),
]

a = Analysis(
    ["main.py"],
    pathex=[os.path.abspath(".")],
    binaries=[],
    datas=added_files,
    hiddenimports=[
        "flask",
        "flask.templating",
        "jinja2",
        "jinja2.ext",
        "bs4",
        "bs4.builder",
        "bs4.builder._html5lib",
        "bs4.builder._lxml",
        "bs4.builder._htmlparser",
        "PIL",
        "PIL.Image",
        "PIL.ImageDraw",
        "PIL.ImageFont",
        "PIL.ImageStat",
        "rich",
        "rich.console",
        "rich.table",
        "rich.progress",
        "rich.live",
        "rich.panel",
        "rich.text",
        "rich.prompt",
        "rich.layout",
        "rich.columns",
        "rich.markdown",
        "rich.align",
        "pyfiglet",
        "pyfiglet.fonts",
        "requests",
        "requests.adapters",
        "requests.auth",
        "urllib3",
        "certifi",
        "charset_normalizer",
        "idna",
        "werkzeug",
        "werkzeug.serving",
        "werkzeug.routing",
        "click",
        "itsdangerous",
        "tkinter",
        "tkinter.ttk",
        "tkinter.scrolledtext",
        "tkinter.filedialog",
        "tkinter.messagebox",
        "difflib",
        "concurrent.futures",
        "threading",
        "zipfile",
        "hashlib",
        "uuid",
        "math",
        "queue",
        "collections",
    ],
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=[
        "matplotlib",
        "numpy",
        "pandas",
        "scipy",
        "cv2",
        "tensorflow",
        "torch",
        "PyQt5",
        "PyQt6",
        "PySide2",
        "PySide6",
        "wx",
    ],
    win_no_prefer_redirects=False,
    win_private_assemblies=False,
    cipher=block_cipher,
    noarchive=False,
)

pyz = PYZ(a.pure, a.zipped_data, cipher=block_cipher)

exe = EXE(
    pyz,
    a.scripts,
    a.binaries,
    a.zipfiles,
    a.datas,
    [],
    name="Mangadeck",
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=True,
    upx_exclude=[],
    runtime_tmpdir=None,
    console=True,      # set False for GUI-only, True to see logs
    disable_windowed_traceback=False,
    target_arch=None,
    codesign_identity=None,
    entitlements_file=None,
    icon="docs/assets/icon.ico",  # remove if you have no icon file
)
```

Build with:

```bash
pyinstaller mangadeck.spec
```

#### Running the built executable

```batch
# Web dashboard (default)
dist\Mangadeck.exe

# Other modes
dist\Mangadeck.exe --mode tui
dist\Mangadeck.exe --mode gui
dist\Mangadeck.exe --mode cli --search "Berserk"
dist\Mangadeck.exe --mode headless --port 5000
```

---

### macOS — `.app`

#### Build command

```bash
pyinstaller --noconfirm --onefile \
  --name "Mangadeck" \
  --add-data "web/templates:web/templates" \
  --add-data "web/static:web/static" \
  --hidden-import "flask" \
  --hidden-import "bs4" \
  --hidden-import "PIL" \
  --hidden-import "rich" \
  --hidden-import "pyfiglet" \
  --hidden-import "requests" \
  main.py
```

> **Note:** On macOS the `--add-data` separator is `:` not `;`.

#### Build an `.app` bundle

```bash
pyinstaller --noconfirm --windowed \
  --name "Mangadeck" \
  --add-data "web/templates:web/templates" \
  --add-data "web/static:web/static" \
  --hidden-import "flask" \
  --hidden-import "bs4" \
  --hidden-import "PIL" \
  --hidden-import "rich" \
  --hidden-import "pyfiglet" \
  --hidden-import "requests" \
  main.py
```

The `.app` bundle is created at `dist/Mangadeck.app`.

#### Codesigning (optional, required for distribution)

```bash
# Sign with your Apple Developer identity
codesign --deep --force --verify --verbose \
  --sign "Developer ID Application: Your Name (TEAMID)" \
  dist/Mangadeck.app

# Verify
codesign --verify --verbose dist/Mangadeck.app
```

#### Run

```bash
# From terminal
dist/Mangadeck

# Or double-click dist/Mangadeck.app in Finder
# Dashboard opens at http://127.0.0.1:5000
```

---

### Linux — ELF binary

#### Build command

```bash
pyinstaller --noconfirm --onefile \
  --name "mangadeck" \
  --add-data "web/templates:web/templates" \
  --add-data "web/static:web/static" \
  --hidden-import "flask" \
  --hidden-import "bs4" \
  --hidden-import "PIL" \
  --hidden-import "rich" \
  --hidden-import "pyfiglet" \
  --hidden-import "requests" \
  main.py
```

#### Run

```bash
chmod +x dist/mangadeck
./dist/mangadeck
./dist/mangadeck --mode tui
./dist/mangadeck --mode cli --search "One Piece"
```

#### Install system-wide (optional)

```bash
sudo cp dist/mangadeck /usr/local/bin/mangadeck
mangadeck --mode web
```

#### Create a `.desktop` entry (optional)

```bash
cat > ~/.local/share/applications/mangadeck.desktop << EOF
[Desktop Entry]
Name=Mangadeck
Comment=Multi-source manga downloader
Exec=/usr/local/bin/mangadeck --mode gui
Icon=/usr/share/icons/mangadeck.png
Terminal=false
Type=Application
Categories=Graphics;Viewer;
EOF
```

---

### Build Script — All Platforms

Save as `build.py` in the repo root and run with `python build.py`:

```python
#!/usr/bin/env python3
"""
Mangadeck build script.
Detects platform and runs the correct PyInstaller command.
Usage: python build.py [--onedir] [--console]
"""

import sys
import os
import subprocess
import argparse
import shutil
import platform

def main():
    parser = argparse.ArgumentParser(description="Build Mangadeck executable")
    parser.add_argument("--onedir", action="store_true",
                        help="Build as folder (faster startup) instead of single file")
    parser.add_argument("--console", action="store_true",
                        help="Show console window (useful for debugging)")
    parser.add_argument("--upx", action="store_true",
                        help="Use UPX compression (must be installed)")
    args = parser.parse_args()

    system = platform.system()
    is_windows = system == "Windows"
    is_mac = system == "Darwin"
    is_linux = system == "Linux"

    # Data separator differs by OS
    sep = ";" if is_windows else ":"

    name = "Mangadeck" if (is_windows or is_mac) else "mangadeck"

    hidden = [
        "flask", "flask.templating", "jinja2", "jinja2.ext",
        "bs4", "bs4.builder", "bs4.builder._htmlparser",
        "PIL", "PIL.Image", "PIL.ImageDraw", "PIL.ImageFont", "PIL.ImageStat",
        "rich", "rich.console", "rich.table", "rich.progress",
        "rich.live", "rich.panel", "rich.text", "rich.prompt",
        "pyfiglet", "pyfiglet.fonts",
        "requests", "requests.adapters", "urllib3", "certifi",
        "werkzeug", "werkzeug.serving", "click", "itsdangerous",
        "tkinter", "tkinter.ttk", "tkinter.scrolledtext",
        "tkinter.filedialog", "tkinter.messagebox",
        "difflib", "concurrent.futures", "threading", "zipfile",
        "hashlib", "uuid", "math", "queue", "collections",
    ]

    cmd = [sys.executable, "-m", "PyInstaller", "--noconfirm"]

    if args.onedir:
        cmd.append("--onedir")
    else:
        cmd.append("--onefile")

    cmd += ["--name", name]

    # Windowed vs console
    if not args.console and (is_windows or is_mac):
        cmd.append("--windowed")

    # Data files
    cmd += [
        "--add-data", f"web/templates{sep}web/templates",
        "--add-data", f"web/static{sep}web/static",
    ]

    # Hidden imports
    for h in hidden:
        cmd += ["--hidden-import", h]

    # Excludes
    excludes = ["matplotlib", "numpy", "pandas", "scipy", "cv2",
                 "tensorflow", "torch", "PyQt5", "PyQt6"]
    for e in excludes:
        cmd += ["--exclude-module", e]

    # UPX
    if not args.upx:
        cmd.append("--noupx")

    # Icon (optional)
    icon_win = "docs/assets/icon.ico"
    icon_mac = "docs/assets/icon.icns"
    if is_windows and os.path.exists(icon_win):
        cmd += ["--icon", icon_win]
    elif is_mac and os.path.exists(icon_mac):
        cmd += ["--icon", icon_mac]

    cmd.append("main.py")

    print(f"\n  Building Mangadeck for {system}")
    print(f"  Mode: {'folder' if args.onedir else 'single file'}")
    print(f"  Console: {args.console}")
    print()

    result = subprocess.run(cmd)

    if result.returncode == 0:
        dist = os.path.join("dist", name + (".exe" if is_windows else ""))
        if os.path.exists(dist):
            size = os.path.getsize(dist)
            print(f"\n  Build successful: {dist}")
            print(f"  Size: {size / 1048576:.1f} MB")
        else:
            dist_dir = os.path.join("dist", name)
            if os.path.isdir(dist_dir):
                print(f"\n  Build successful: {dist_dir}/")
        print()
    else:
        print("\n  Build failed. Check output above.")
        sys.exit(1)

if __name__ == "__main__":
    main()
```

**Usage:**

```bash
# Default: single file, no console window
python build.py

# With console output visible (useful for debugging crashes)
python build.py --console

# Faster startup (folder mode instead of single file)
python build.py --onedir

# With UPX compression (smaller file, requires upx installed)
python build.py --upx
```

---

### Common Build Issues

#### `ModuleNotFoundError` at runtime

The executable is missing a hidden import. Identify the missing module from the error output and add it to `--hidden-import` in your build command or spec file.

```bash
# Find what module is missing from the error, then add:
pyinstaller ... --hidden-import "missing.module.name" main.py
```

#### Templates or static files not found

Ensure the `--add-data` paths match your directory structure exactly. The format is:

```
# Windows
--add-data "source;destination"

# macOS / Linux
--add-data "source:destination"
```

Both `source` and `destination` are relative to the spec file location.

#### Tkinter not found on Linux

```bash
# Ubuntu / Debian
sudo apt install python3-tk

# Fedora
sudo dnf install python3-tkinter

# Arch
sudo pacman -S tk
```

Then rebuild.

#### Antivirus false positive on Windows

PyInstaller executables sometimes trigger Windows Defender or other antivirus software. This is a known false positive. To distribute:

1. Submit the file to [VirusTotal](https://www.virustotal.com) for analysis
2. Add a code signing certificate if distributing publicly
3. Or distribute as a zip with instructions to add an exclusion

#### macOS Gatekeeper

```bash
# If macOS blocks the app from opening
xattr -cr dist/Mangadeck.app

# Or right-click > Open in Finder to bypass Gatekeeper once
```

#### UPX not found

UPX is optional. Either install it or remove `--upx` from your command:

```bash
# Windows (via scoop)
scoop install upx

# macOS (via brew)
brew install upx

# Ubuntu / Debian
sudo apt install upx
```

---

### Output File Sizes

Approximate sizes after build (varies by platform and Python version):

| Build type | Approximate size |
|-----------|-----------------|
| Single file, no UPX | 45 – 65 MB |
| Single file, with UPX | 20 – 35 MB |
| Folder (onedir) | 90 – 130 MB total, faster startup |

---

### Distributing the Executable

#### Windows

Bundle the executable with a simple launcher batch file:

```batch
@echo off
start "" "%~dp0Mangadeck.exe" --mode web
timeout /t 2 /nobreak >nul
start "" "http://127.0.0.1:5000"
```

#### macOS

Create a DMG for distribution:

```bash
# Install create-dmg
brew install create-dmg

create-dmg \
  --volname "Mangadeck" \
  --window-pos 200 120 \
  --window-size 600 400 \
  --icon-size 100 \
  --icon "Mangadeck.app" 175 190 \
  --hide-extension "Mangadeck.app" \
  --app-drop-link 425 190 \
  "Mangadeck.dmg" \
  "dist/"
```

#### Linux

Create a tar.gz archive:

```bash
mkdir Mangadeck-linux
cp dist/mangadeck Mangadeck-linux/
cp README.md Mangadeck-linux/
chmod +x Mangadeck-linux/mangadeck
tar -czf Mangadeck-linux-x64.tar.gz Mangadeck-linux/
```

---