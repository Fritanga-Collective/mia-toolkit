# -*- mode: python ; coding: utf-8 -*-
# PyInstaller spec for the macOS .app. Run from the repo root:
#
#     pyinstaller packaging/macos/mia.spec --noconfirm
#
# Produces dist/MIA Toolkit.app (then sign + notarize with
# packaging/macos/sign_notarize.sh).
#
# Universal binary: building a true universal2 app requires a universal2 Python
# (the python.org installer). On an arm64-only interpreter (e.g. pyenv/Homebrew)
# this builds arm64-only — fine for local testing. Set MIA_TARGET_ARCH=universal2
# in the environment once a universal2 interpreter is in use.

import os
import sys

from PyInstaller.utils.hooks import collect_data_files, collect_submodules

# Resolve the repo root from the spec's location so the build works no matter
# the current directory.
try:
    SPEC_DIR = SPECPATH  # injected by PyInstaller when running a .spec
except NameError:
    SPEC_DIR = os.getcwd()
REPO = os.path.abspath(os.path.join(SPEC_DIR, "..", ".."))

# collect_submodules("mia_core") below runs at spec-eval time, BEFORE
# Analysis(pathex=[REPO]) influences resolution — so make mia_core importable
# now (works even if PyInstaller is launched from outside the repo root or
# without an editable install). Force REPO to the FRONT (de-duped) so the repo's
# source wins over any installed copy → reproducible builds regardless of
# PYTHONPATH / site-packages ordering.
sys.path = [REPO] + [p for p in sys.path if p != REPO]

TARGET_ARCH = os.environ.get("MIA_TARGET_ARCH") or None  # 'universal2' when ready
# CI sets MIA_VERSION from the release tag so the bundle's Info.plist matches.
VERSION = os.environ.get("MIA_VERSION") or "0.1.0"

# pydicom/openpyxl pull some submodules dynamically; gather them explicitly.
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
    # Keep the bundle pure-Python (no arch-specific wheels) so universal2 stays
    # achievable. Our flows never touch pixel arrays, so numpy isn't needed.
    excludes=["numpy", "pytest", "PIL"],
    noarchive=False,
)
pyz = PYZ(a.pure)

exe = EXE(
    pyz,
    a.scripts,
    [],
    exclude_binaries=True,
    name="mia",
    debug=False,
    strip=False,
    upx=False,
    console=False,
    target_arch=TARGET_ARCH,
    codesign_identity=None,   # signing is done afterwards by sign_notarize.sh
    entitlements_file=None,
)

coll = COLLECT(exe, a.binaries, a.datas, strip=False, upx=False, name="mia")

app = BUNDLE(
    coll,
    name="MIA Toolkit.app",
    icon=os.path.join(REPO, "packaging/macos/app.icns"),
    bundle_identifier="com.fritanga.miatoolkit",
    version=VERSION,
    info_plist={
        "CFBundleName": "MIA Toolkit",
        "CFBundleDisplayName": "MIA Toolkit",
        "CFBundleShortVersionString": VERSION,
        "CFBundleVersion": VERSION,
        "LSMinimumSystemVersion": "12.0",
        "NSHighResolutionCapable": True,
        "LSApplicationCategoryType": "public.app-category.medical",
        # The app reads removable volumes (CDs/USB); explain the access prompt.
        "NSRemovableVolumesUsageDescription":
            "Access removable drives to copy imaging discs and write the archive.",
    },
)
