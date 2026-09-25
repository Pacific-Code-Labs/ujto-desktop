#!/usr/bin/env bash
# dist/Ujto (PyInstaller one-dir) → dist/Ujto-linux-x64.AppImage. Needs appimagetool on PATH
# (CI downloads it). The system must provide WebKitGTK 4.1 (libwebkit2gtk-4.1-0).
set -euo pipefail
cd "$(dirname "$0")/../.."
APPDIR=build/Ujto.AppDir
rm -rf "$APPDIR" && mkdir -p "$APPDIR/usr/lib/ujto" "$APPDIR/usr/share/applications" "$APPDIR/usr/share/icons/hicolor/512x512/apps"
cp -a dist/Ujto/. "$APPDIR/usr/lib/ujto/"
cp packaging/linux/ujto.desktop "$APPDIR/ujto.desktop"
cp packaging/linux/ujto.desktop "$APPDIR/usr/share/applications/ujto.desktop"
cp assets/icon.png "$APPDIR/ujto.png"
cp assets/icon.png "$APPDIR/usr/share/icons/hicolor/512x512/apps/ujto.png"
cat > "$APPDIR/AppRun" <<'RUN'
#!/bin/sh
HERE="$(dirname "$(readlink -f "$0")")"
exec "$HERE/usr/lib/ujto/Ujto" "$@"
RUN
chmod +x "$APPDIR/AppRun"
ARCH=x86_64 appimagetool "$APPDIR" dist/Ujto-linux-x64.AppImage
