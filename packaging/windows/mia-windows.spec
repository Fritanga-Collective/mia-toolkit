# -*- mode: python ; coding: utf-8 -*-
# PyInstaller spec for the Windows build. Run from the repo root (on Windows):
#
#     pyinstaller packaging/windows/mia-windows.spec --noconfirm
#
# Produces dist/MIAToolkit/ (a one-dir build) whose "Medical Imaging
# Archiver.exe" the Inno Setup script (installer.iss) wraps into an installer.
# Reuses the same entry point as macOS (packaging/macos/launch.py).

import os
import sys

from PyInstaller.utils.hooks import collect_data_files, collect_submodules

try:
    SPEC_DIR = SPECPATH
except NameError:
    SPEC_DIR = os.getcwd()
REPO = os.path.abspath(os.path.join(SPEC_DIR, "..", ".."))

# collect_submodules("mia_core") below runs at spec-eval time, BEFORE
# Analysis(pathex=[REPO]) influences resolution — so make mia_core importable
# now (works even if PyInstaller is launched from outside the repo root or
# without an editable install).
if REPO not in sys.path:
    sys.path.insert(0, REPO)

# CI sets MIA_VERSION from the release tag.
VERSION = os.environ.get("MIA_VERSION") or "0.1.0"

# mia_core exposes its worker modules via a lazy PEP-562 __getattr__, so the
# static analyzer can miss some; collect them explicitly too.
hidden = (collect_submodules("pydicom") + collect_submodules("openpyxl")
          + collect_submodules("mia_core"))
datas = collect_data_files("pydicom") + [
    (os.path.join(REPO, "mia/i18n/locale"), "mia/i18n/locale"),
    (os.path.join(REPO, "mia/gui/assets"), "mia/gui/assets"),
]

a = Analysis(
    [os.path.join(REPO, "packaging/macos/launch.py")],
    pathex=[REPO],
    binaries=[],
    datas=datas,
    hiddenimports=hidden,
    hookspath=[],
    runtime_hooks=[],
    excludes=["numpy", "pytest", "PIL"],
    noarchive=False,
)
pyz = PYZ(a.pure)

exe = EXE(
    pyz,
    a.scripts,
    [],
    exclude_binaries=True,
    name="MIA Toolkit",
    debug=False,
    strip=False,
    upx=False,
    console=False,         # GUI app — no console window
    icon=os.path.join(REPO, "packaging/windows/app.ico"),
)

coll = COLLECT(exe, a.binaries, a.datas, strip=False, upx=False, name="MIAToolkit")
