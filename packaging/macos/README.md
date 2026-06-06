# macOS packaging — signing & notarization (validated runbook)

Builds a double-clickable `.app`, then signs, notarizes, and staples it into a
distributable `.dmg`. This flow has been **run end-to-end** with a real
Developer ID certificate; it is no longer a scaffold.

```
packaging/macos/
├── launch.py          # frozen-app entry point (starts the GUI)
├── mia.spec           # PyInstaller spec -> dist/MIA Toolkit.app
├── entitlements.plist # hardened-runtime entitlements (validated set, see below)
└── sign_notarize.sh   # sign + dmg + notarize + staple + Gatekeeper check
```

## 1. Build the app (no cert needed)

From the repo root, in the project venv:

```bash
pip install -e ".[build]"
pyinstaller packaging/macos/mia.spec --noconfirm
open "dist/MIA Toolkit.app"
```

**Universal binary:** a true `universal2` build needs a universal2 Python (the
[python.org](https://www.python.org/downloads/macos/) installer). On an
arm64-only interpreter this produces an arm64-only app. With a universal2
interpreter, build with `MIA_TARGET_ARCH=universal2 pyinstaller …`, then check
every embedded binary is fat:

```bash
find "dist/MIA Toolkit.app" -type f -perm +111 \
  -exec sh -c 'lipo -archs "$1" 2>/dev/null | grep -q "x86_64 arm64" || echo "NOT universal: $1"' _ {} \;
```

## 2. One-time credential setup (what we actually did)

1. **CSR + key** (no Keychain Access GUI needed):
   ```bash
   openssl genrsa -out devid.key 2048
   openssl req -new -key devid.key -out DeveloperID.csr \
     -subj "/emailAddress=you@example.com/CN=anything/C=MX"
   ```
   Apple **ignores the subject fields** — the certificate's name comes from the
   Developer Program enrollment (Individual = your legal name; an organization
   name requires an Organization enrollment with a D-U-N-S number).
2. Upload the CSR at developer.apple.com → Certificates → **Developer ID
   Application** → download the `.cer`.
3. Import both into the login keychain:
   ```bash
   security import devid.key -k ~/Library/Keychains/login.keychain-db -T /usr/bin/codesign
   security import developerID_application.cer -k ~/Library/Keychains/login.keychain-db -T /usr/bin/codesign
   security find-identity -p codesigning -v   # should list the identity
   ```
4. **Notarization credentials** — create an app-specific password at
   account.apple.com, then:
   ```bash
   xcrun notarytool store-credentials mia-notary \
     --apple-id YOU@example.com --team-id TEAMID --password app-specific-pw
   ```

## 3. Sign + notarize + staple

```bash
MIA_SIGN_ID="Developer ID Application: NAME (TEAMID)" \
MIA_NOTARY_PROFILE="mia-notary" \
VERSION="X.Y.Z" \
packaging/macos/sign_notarize.sh
```

The script signs **inside-out** (every bundled `.dylib`/`.so` first — ~63 of
them — then frameworks, then the bundle with the entitlements), builds the
DMG, signs it, submits to Apple's notary service (a few minutes, full log
printed on failure), staples the ticket to both the app and the DMG, and runs
a Gatekeeper assessment.

**Entitlements** (`entitlements.plist`) are the minimal validated set a
PyInstaller/Tk app needs under the hardened runtime: unsigned-executable
memory, JIT, dyld environment variables, and disabled library validation. The
signed app has been verified to launch with exactly these four.

## 4. CI (automatic on every tag once secrets exist)

`release.yml` runs the same script when these repo secrets are set:

| Secret | Value |
|---|---|
| `MACOS_SIGN_ID` | `Developer ID Application: NAME (TEAMID)` |
| `MACOS_CERT_P12` | base64 of the exported .p12 (identity + private key) |
| `MACOS_CERT_PASSWORD` | the .p12 password |
| `APPLE_ID` | the Apple ID email |
| `APPLE_TEAM_ID` | the 10-char Team ID |
| `APPLE_APP_PASSWORD` | the app-specific password |

Export the `.p12` from Keychain Access (My Certificates → right-click the
Developer ID identity → Export) or via `security export`, then
`base64 -i devid.p12 | pbcopy`.

Without the secrets the workflow still builds an **unsigned** `.dmg`, so the
pipeline never blocks on credentials.

## Troubleshooting

- `errSecInternalComponent` while signing in CI → keychain locked or partition
  list unset; the workflow handles both (see release.yml).
- Notarization "Invalid" → `xcrun notarytool log <id> --keychain-profile
  mia-notary` lists per-file issues; usual culprits are an unsigned nested
  binary (the script signs inside-out to prevent this) or a missing secure
  timestamp (`--timestamp` is on every codesign call).
- Gatekeeper complaints after stapling → `spctl -a -t open --context
  context:primary-signature -vv dist/MIA-Toolkit-X.Y.Z.dmg`.

## Remaining placeholders

- An `app.icns` icon (mia.spec has `icon=None`).
- Bundle identifier `com.fritanga.miatoolkit` is set and final.
