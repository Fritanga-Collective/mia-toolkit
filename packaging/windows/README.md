# Windows packaging

Builds a per-user installer (`.exe`) — **on Windows** (PyInstaller can't
cross-compile from macOS, so this normally runs on the Windows CI runner).

```
packaging/windows/
├── mia-windows.spec   # PyInstaller spec -> dist/MIAToolkit/ (one-dir build)
└── installer.iss      # Inno Setup -> dist/MIA-Toolkit-Setup-<ver>.exe
```

## Build (on a Windows machine or runner)

```powershell
pip install -e ".[build]"
pyinstaller packaging\windows\mia-windows.spec --noconfirm
# Inno Setup (install via: choco install innosetup)
& "C:\Program Files (x86)\Inno Setup 6\ISCC.exe" packaging\windows\installer.iss
# -> dist\MIA-Toolkit-Setup-0.1.0.exe
```

The installer is **per-user** (`PrivilegesRequired=lowest`) — no admin prompt,
installs to `%LOCALAPPDATA%\Programs`.

## Signing (later)

v1 ships **unsigned** — users will see a SmartScreen "unknown publisher" prompt
(More info → Run anyway). When a Windows certificate is available, sign the
installer before publishing, e.g. with `signtool.exe` or **Microsoft Trusted
Signing** (cloud-based, no hardware token, CI-friendly — the preferred route).
Use an **RSA** certificate (Smart App Control rejects ECC). Insert the signing
step in the Windows job of `.github/workflows/release.yml`.
