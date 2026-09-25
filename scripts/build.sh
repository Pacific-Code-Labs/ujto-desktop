#!/usr/bin/env bash
# Build the app for this OS into dist/ (PyInstaller one-dir), then the installer:
#   macOS  → dist/Ujto-mac-<arch>.dmg
#   Linux  → dist/Ujto-linux-x64.AppImage and dist/Ujto-linux-amd64.deb
#   Windows (Git Bash) → dist/Ujto/ (the Inno Setup step runs in CI: packaging/windows/ujto.iss)
set -euo pipefail
cd "$(dirname "$0")/.."
PY="${PYTHON:-python3}"
"$PY" -m pip install -q -r requirements-dev.txt pillow
[[ -x vendor/deno || -f vendor/deno.exe ]] || bash scripts/fetch-deno.sh
"$PY" scripts/make-icons.py
"$PY" -m PyInstaller --noconfirm --clean packaging/ujto.spec
VERSION="$("$PY" -c 'import ujto_desktop; print(ujto_desktop.__version__)')"

case "$(uname -s)" in
  Darwin)
    ARCH="$(uname -m)"; [[ "$ARCH" == "x86_64" ]] && ARCH=x64
    rm -f "dist/Ujto-mac-${ARCH}.dmg"
    bash scripts/sign-macos.sh app dist/Ujto.app          # no-op without MACOS_SIGN_IDENTITY
    hdiutil create -volname "Ujtö̀" -srcfolder dist/Ujto.app -ov -format UDZO "dist/Ujto-mac-${ARCH}.dmg"
    bash scripts/sign-macos.sh dmg "dist/Ujto-mac-${ARCH}.dmg"
    ;;
  Linux)
    bash packaging/linux/build-appimage.sh "$VERSION"
    bash packaging/linux/build-deb.sh "$VERSION"
    ;;
  *) echo "Windows: build the installer with Inno Setup (packaging/windows/ujto.iss)" ;;
esac
ls -la dist
