#!/usr/bin/env bash
# Download the Deno binary for this platform into vendor/ (bundled: yt-dlp needs a JS runtime
# to solve YouTube's player challenges). Same version as the transcription worker.
set -euo pipefail
VERSION="${DENO_VERSION:-2.9.4}"
case "$(uname -s)-$(uname -m)" in
  Darwin-arm64) TARGET=aarch64-apple-darwin ;;
  Darwin-x86_64) TARGET=x86_64-apple-darwin ;;
  Linux-x86_64) TARGET=x86_64-unknown-linux-gnu ;;
  MINGW*|MSYS*|CYGWIN*) TARGET=x86_64-pc-windows-msvc ;;
  *) echo "Unsupported platform $(uname -s)-$(uname -m)" >&2; exit 1 ;;
esac
cd "$(dirname "$0")/.."
mkdir -p vendor build
curl -fsSL -o build/deno.zip "https://github.com/denoland/deno/releases/download/v${VERSION}/deno-${TARGET}.zip"
unzip -o -q build/deno.zip -d vendor
chmod +x vendor/deno* 2>/dev/null || true
ls -la vendor
