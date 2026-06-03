# macOS packaging

Builds a double-clickable `.app`, then (once you have an Apple Developer cert)
signs, notarizes, and staples it into a distributable `.dmg`.

```
packaging/macos/
├── launch.py          # frozen-app entry point (starts the GUI)
├── mia.spec           # PyInstaller spec -> dist/Medical Imaging Archiver.app
├── entitlements.plist # hardened-runtime entitlements
└── sign_notarize.sh   # sign + dmg + notarize + staple (needs the cert)
```

## 1. Build the app (no cert needed)

From the repo root, in the project venv:

```bash
pip install pyinstaller          # or: pip install -e ".[build]"
pyinstaller packaging/macos/mia.spec --noconfirm
open "dist/Medical Imaging Archiver.app"
```

**Universal binary:** a true `universal2` build needs a universal2 Python (the
[python.org](https://www.python.org/downloads/macos/) installer). On an
arm64-only interpreter (pyenv/Homebrew) this produces an arm64-only app — fine
for testing. When you switch to a universal2 interpreter, build with
`MIA_TARGET_ARCH=universal2 pyinstaller …`, then verify every embedded binary is
fat:

```bash
find "dist/Medical Imaging Archiver.app" -type f -perm +111 \
  -exec sh -c 'lipo -archs "$1" 2>/dev/null | grep -q "x86_64 arm64" || echo "NOT universal: $1"' _ {} \;
```

## 2. Sign + notarize + staple (needs Apple Developer enrollment)

After enrolling and installing a **Developer ID Application** certificate, and
storing notarization credentials once:

```bash
xcrun notarytool store-credentials "mia-notary" \
  --apple-id "you@example.com" --team-id "TEAMID" --password "app-specific-password"
```

then:

```bash
MIA_SIGN_ID="Developer ID Application: Your Name (TEAMID)" \
MIA_NOTARY_PROFILE="mia-notary" \
packaging/macos/sign_notarize.sh
```

The script signs nested binaries inside-out, signs the bundle with the
entitlements, builds and signs the DMG, submits to notarization (printing the
**full log on failure**), staples, and runs a Gatekeeper check.

## Placeholders to update

- Bundle identifier `com.fritanga.miatoolkit` in `mia.spec` (and an `app.icns`
  icon when you have one).
- `MIA_SIGN_ID` / `MIA_NOTARY_PROFILE` come from your Apple account.
