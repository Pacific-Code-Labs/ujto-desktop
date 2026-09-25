# ujto-desktop

**Ujtö̀ for desktop** (macOS, Windows, Linux): the Ujtö̀ dashboard
([app.ujto.jcampos.dev](https://app.ujto.jcampos.dev), repo [ujto-app](https://github.com/Pacific-Code-Labs/ujto-app))
in a native window, plus one thing the web can't do: paste a YouTube link and the audio is
downloaded **from your own computer** and sent for transcription.

Why: YouTube blocks downloads from cloud servers (the transcription worker runs on AWS), but
accepts them from a home connection.

## How it works

- Python 3.12 + [pywebview](https://pywebview.flowrl.com/) shows the deployed dashboard (WebView2 on
  Windows, WKWebView on macOS, WebKitGTK 4.1 on Linux), so the app always has the current UI and
  design system. Sign-in is the normal Cognito sign-in inside the web view (kept between launches).
- `ujto_desktop/bridge.py` is exposed as `window.pywebview.api`. The dashboard calls it from
  `/new` → *Paste a link*:
  1. `probe(url)` — title and duration (yt-dlp, no download) so the plan limit is checked first;
  2. the web app asks the API for a presigned S3 upload (the user's token never leaves the web view);
  3. `download_and_upload(jobId, url, upload)` — yt-dlp downloads the best audio, ffmpeg makes an
     m4a, the file is POSTed to S3, and the temp folder is deleted (success or failure);
  4. the web app starts the job. Progress is pushed to `window.ujtoDesktop.onProgress`.
- The bridge refuses calls unless the window shows the dashboard's origin; links to other sites
  open in the system browser.
- `ujto://new?url=<link>` deep links open the New page with the link filled in.
- Bundled: ffmpeg (`imageio-ffmpeg`) and Deno (JS runtime yt-dlp needs for YouTube).

## Develop

```bash
python3 -m venv .venv && .venv/bin/pip install -r requirements-dev.txt
UJTO_APP_URL=http://localhost:5174 .venv/bin/python -m ujto_desktop   # against a local dashboard
.venv/bin/python -m pytest -q tests
```

## Build and release

`bash scripts/build.sh` builds for the current OS (PyInstaller one-dir, then `.dmg` / AppImage +
`.deb`; Windows uses Inno Setup, `packaging/windows/ujto.iss`).

Tag `vX.Y.Z` (after bumping `ujto_desktop/__init__.py`) → GitHub Actions builds macOS arm64/x64,
Windows x64 and Linux x64 and publishes a release with **stable asset names**, so these links
(used by the landing and the dashboard) always point at the latest version:

| Platform | Asset |
|---|---|
| macOS Apple silicon | `Ujto-mac-arm64.dmg` |
| macOS Intel | `Ujto-mac-x64.dmg` |
| Windows 10/11 | `Ujto-windows-x64.exe` |
| Linux | `Ujto-linux-x64.AppImage`, `Ujto-linux-amd64.deb` |

`https://github.com/Pacific-Code-Labs/ujto-desktop/releases/latest/download/<asset>`

Every Monday CI checks PyPI for a new yt-dlp (YouTube breaks old versions) and opens a PR.

**Signing:** builds are unsigned until an Apple Developer ID (notarization) and a Windows
code-signing certificate are added; until then macOS Gatekeeper and Windows SmartScreen warn
on first launch. After a release, set `"status": "available"` in the landing's
`src/content/download.json` and the dashboard's `src/content/desktop.json` (ujto-admin).

Only process media you have the right to use.
