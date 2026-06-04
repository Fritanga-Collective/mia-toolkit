#!/usr/bin/env bash
# Sign, package, notarize, and staple the macOS app.
#
# SCAFFOLD: this cannot run until you have an Apple Developer membership and a
# "Developer ID Application" certificate in your keychain. It is written so that,
# once you do, it runs end-to-end with two env vars set.
#
# One-time setup (after enrollment):
#   1. Create + install a "Developer ID Application" certificate (Xcode or the
#      Apple Developer site), then confirm it:
#        security find-identity -p codesigning -v
#   2. Store notarization credentials as a reusable keychain profile:
#        xcrun notarytool store-credentials "mia-notary" \
#          --apple-id "you@example.com" --team-id "TEAMID" \
#          --password "app-specific-password"      # or use --key for an API key
#
# Run (from repo root, after `pyinstaller packaging/macos/mia.spec`):
#   MIA_SIGN_ID="Developer ID Application: Your Name (TEAMID)" \
#   MIA_NOTARY_PROFILE="mia-notary" \
#   packaging/macos/sign_notarize.sh
set -euo pipefail

APP="dist/Medical Imaging Archiver.app"
VERSION="${VERSION:-0.1.0}"   # CI passes the tag version; defaults to 0.1.0
DMG="dist/MIA-Toolkit-${VERSION}.dmg"
ENTITLEMENTS="packaging/macos/entitlements.plist"
VOLNAME="Medical Imaging Archiver"

: "${MIA_SIGN_ID:?Set MIA_SIGN_ID to 'Developer ID Application: NAME (TEAMID)'}"
: "${MIA_NOTARY_PROFILE:?Set MIA_NOTARY_PROFILE to your notarytool keychain profile}"

[ -d "$APP" ] || { echo "ERROR: $APP not found — build it first with pyinstaller."; exit 1; }

echo "==> Signing nested libraries (inside-out, hardened runtime)…"
# Sign every embedded Mach-O first; Apple requires inner code signed before the
# bundle. --deep is intentionally avoided (Apple deprecates it).
find "$APP/Contents" \( -name "*.dylib" -o -name "*.so" \) -print0 \
  | while IFS= read -r -d '' lib; do
      codesign --force --options runtime --timestamp --sign "$MIA_SIGN_ID" "$lib"
    done

# Sign any nested frameworks (e.g. Tcl/Tk) if present.
find "$APP/Contents" -type d -name "*.framework" -print0 \
  | while IFS= read -r -d '' fw; do
      codesign --force --options runtime --timestamp --sign "$MIA_SIGN_ID" "$fw"
    done

echo "==> Signing the app bundle with entitlements…"
codesign --force --options runtime --timestamp \
  --entitlements "$ENTITLEMENTS" --sign "$MIA_SIGN_ID" "$APP"

echo "==> Verifying signature…"
codesign --verify --strict --verbose=2 "$APP"

echo "==> Building DMG…"
rm -f "$DMG"
hdiutil create -volname "$VOLNAME" -srcfolder "$APP" -ov -format UDZO "$DMG"

echo "==> Signing DMG…"
codesign --force --timestamp --sign "$MIA_SIGN_ID" "$DMG"

echo "==> Notarizing (this can take a few minutes)…"
set +e
SUBMIT_OUT=$(xcrun notarytool submit "$DMG" \
  --keychain-profile "$MIA_NOTARY_PROFILE" --wait 2>&1)
SUBMIT_RC=$?
echo "$SUBMIT_OUT"
set -e
if [ $SUBMIT_RC -ne 0 ] || echo "$SUBMIT_OUT" | grep -qi "Invalid\|Rejected"; then
  ID=$(echo "$SUBMIT_OUT" | awk '/id:/{print $2; exit}')
  echo "!! Notarization did not succeed. Fetching the log for ${ID}:"
  [ -n "${ID:-}" ] && xcrun notarytool log "$ID" \
    --keychain-profile "$MIA_NOTARY_PROFILE" || true
  exit 1
fi

echo "==> Stapling…"
xcrun stapler staple "$APP"
xcrun stapler staple "$DMG"
xcrun stapler validate "$DMG"

echo "==> Gatekeeper assessment…"
spctl -a -t open --context context:primary-signature -vv "$DMG" || true

echo "✓ Done: $DMG (signed, notarized, stapled)."
