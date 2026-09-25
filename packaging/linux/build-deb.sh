#!/usr/bin/env bash
# dist/Ujto → dist/Ujto-linux-amd64.deb (installs to /opt/ujto, registers ujto:// links).
set -euo pipefail
VERSION="${1:?version}"
cd "$(dirname "$0")/../.."
PKG=build/deb
rm -rf "$PKG" && mkdir -p "$PKG/DEBIAN" "$PKG/opt/ujto" "$PKG/usr/bin" "$PKG/usr/share/applications" "$PKG/usr/share/icons/hicolor/512x512/apps"
cp -a dist/Ujto/. "$PKG/opt/ujto/"
ln -s /opt/ujto/Ujto "$PKG/usr/bin/ujto"
cp packaging/linux/ujto.desktop "$PKG/usr/share/applications/ujto.desktop"
cp assets/icon.png "$PKG/usr/share/icons/hicolor/512x512/apps/ujto.png"
cat > "$PKG/DEBIAN/control" <<CONTROL
Package: ujto
Version: ${VERSION}
Section: video
Priority: optional
Architecture: amd64
Depends: libwebkit2gtk-4.1-0, libgtk-3-0, gir1.2-webkit2-4.1
Maintainer: Pacific Code Labs <noreply@jcampos.dev>
Homepage: https://ujto.jcampos.dev
Description: Ujtö̀ desktop — from video to word
 The Ujtö̀ dashboard in a desktop window. Paste a YouTube link and the audio is
 downloaded from your own computer and sent for transcription.
CONTROL
cat > "$PKG/DEBIAN/postinst" <<'POST'
#!/bin/sh
set -e
command -v update-desktop-database >/dev/null && update-desktop-database -q /usr/share/applications || true
POST
chmod 755 "$PKG/DEBIAN/postinst"
dpkg-deb --build --root-owner-group "$PKG" dist/Ujto-linux-amd64.deb
