# -*- mode: python ; coding: utf-8 -*-
# PyInstaller spec for the Windows build. Run from the repo root (on Windows):
#
#     pyinstaller packaging/windows/mia-windows.spec --noconfirm
#
# Produces dist/MIAToolkit/ (a one-dir build) whose "Medical Imaging
# Archiver.exe" the Inno Setup script (installer.iss) wraps into an installer.
# Reuses the same entry point as macOS (packaging/macos/launch.py).

import os

from PyInstaller.utils.hooks import collect_data_files, collect_submodules

try:
    SPEC_DIR = SPECPATH
except NameError:
    SPEC_DIR = os.getcwd()
REPO = os.path.abspath(os.path.join(SPEC_DIR, "..", ".."))

VERSION = "0.1.0"

hidden = collect_submodules("pydicom") + collect_submodules("openpyxl")
datas = collect_data_files("pydicom") + [
    (os.path.join(REPO, "mia/i18n/locale"), "mia/i18n/locale"),
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
    name="Medical Imaging Archiver",
    debug=False,
    strip=False,
    upx=False,
    console=False,         # GUI app — no console window
    icon=None,             # add packaging/windows/app.ico later
)

coll = COLLECT(exe, a.binaries, a.datas, strip=False, upx=False, name="MIAToolkit")
