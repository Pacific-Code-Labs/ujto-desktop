#!/usr/bin/env bash
# Sign (and optionally notarize) the macOS build. No-op unless MACOS_SIGN_IDENTITY is set, so
# unsigned local/CI builds keep working.
#
#   bash scripts/sign-macos.sh app  dist/Ujto.app           # sign every Mach-O inside, then the app
#   bash scripts/sign-macos.sh dmg  dist/Ujto-mac-arm64.dmg  # sign the dmg, notarize, staple
#
# Env:
#   MACOS_SIGN_IDENTITY  "Developer ID Application: Name (TEAMID)" (in the keychain)
#   Notarization, either an App Store Connect API key (recommended):
#     APPLE_API_KEY_PATH (.p8 file), APPLE_API_KEY_ID, APPLE_API_ISSUER
#   or an Apple ID:  APPLE_ID, APPLE_APP_PASSWORD (app-specific), APPLE_TEAM_ID
set -euo pipefail
cd "$(dirname "$0")/.."
KIND="${1:?app|dmg}"
TARGET="${2:?path}"
if [[ -z "${MACOS_SIGN_IDENTITY:-}" ]]; then
  echo "MACOS_SIGN_IDENTITY not set: leaving ${TARGET} unsigned"
  exit 0
fi
ENTITLEMENTS="packaging/macos/entitlements.plist"
sign() { codesign --force --timestamp --options runtime --entitlements "$ENTITLEMENTS" --sign "$MACOS_SIGN_IDENTITY" "$@"; }

case "$KIND" in
  app)
    # Inside-out: nested binaries (Python libs, ffmpeg, deno) first, the bundle last.
    while IFS= read -r -d '' f; do
      if file -b "$f" | grep -q "Mach-O"; then sign "$f"; fi
    done < <(find "$TARGET/Contents" -type f -print0)
    sign "$TARGET"
    codesign --verify --deep --strict --verbose=2 "$TARGET"
    ;;
  dmg)
    codesign --force --timestamp --sign "$MACOS_SIGN_IDENTITY" "$TARGET"
    if [[ -n "${APPLE_API_KEY_PATH:-}" ]]; then
      xcrun notarytool submit "$TARGET" --key "$APPLE_API_KEY_PATH" --key-id "$APPLE_API_KEY_ID" --issuer "$APPLE_API_ISSUER" --wait
    elif [[ -n "${APPLE_ID:-}" ]]; then
      xcrun notarytool submit "$TARGET" --apple-id "$APPLE_ID" --password "$APPLE_APP_PASSWORD" --team-id "$APPLE_TEAM_ID" --wait
    else
      echo "No notarization credentials: signed but not notarized (Gatekeeper will still warn)" >&2
      exit 0
    fi
    xcrun stapler staple "$TARGET"
    spctl --assess --type open --context context:primary-signature --verbose=2 "$TARGET" || true
    ;;
  *) echo "Unknown kind $KIND" >&2; exit 1 ;;
esac
