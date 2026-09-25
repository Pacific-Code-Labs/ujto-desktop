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

## Microsoft Store

Two editions, chosen at build time with `UJTO_EDITION` (baked into the app as `edition.txt`):

| Edition | What it has | Where it ships |
|---|---|---|
| `full` (default) | Dashboard + on-device link downloads (yt-dlp, ffmpeg, Deno) + GitHub update check | GitHub Releases, website |
| `store` | Dashboard only (uploads, history, notifications, `ujto://` links); ~33 MB | Microsoft Store |

Store policy rejects apps that download content from services like YouTube against their terms,
so submit the **store** edition first; the full one is built too if you want to try it. In the
store edition the bridge reports `capabilities().download = false` and the dashboard's Link tab
falls back to the server.

Every Windows CI build produces both packages in the `ujto-msstore` artifact
(`scripts/build-msix.ps1`, `packaging/windows/msix/AppxManifest.xml`):
`Ujto-windows-x64-store.msix` and `Ujto-windows-x64.msix`. They are unsigned — the Store signs them —
and are not attached to GitHub releases.

**First submission (manual):**
1. [Partner Center](https://partner.microsoft.com/dashboard) → Apps and games → New product → MSIX
   or PWA app → reserve the name (e.g. "Ujtö̀").
2. Product → **Product identity**: copy *Package/Identity/Name*, *Package/Identity/Publisher* (`CN=…`)
   and *Package/Properties/PublisherDisplayName* into repository **variables**
   `MSSTORE_IDENTITY_NAME`, `MSSTORE_PUBLISHER`, `MSSTORE_PUBLISHER_DISPLAY_NAME`.
3. Tag a release (or run the workflow manually); download the `ujto-msstore` artifact.
4. New submission → Packages → upload the `.msix`; fill in pricing (free), properties, age rating,
   store listing (EN/ES; screenshots of the dashboard) and a privacy policy URL; submit.
   Mention in the notes that the app needs a Ujtö̀ account (give certification a test login).

**Later submissions (optional automation):** create an Azure AD app linked to Partner Center
(Account settings → User management → Azure AD applications, role *Manager*), then set variables
`MSSTORE_PUBLISH=true`, `MSSTORE_APP_ID` (Store ID, e.g. `9N…`), `MSSTORE_EDITION` (`store`/`full`)
and secrets `PARTNER_CENTER_TENANT_ID`, `PARTNER_CENTER_SELLER_ID`, `PARTNER_CENTER_CLIENT_ID`,
`PARTNER_CENTER_CLIENT_SECRET`. Each `v*` tag then creates a **draft** submission with the new
package (`msstore publish --noCommit`); review and submit it in Partner Center.

## Signing (off until configured)

The workflow signs only when repository **variables** turn it on (Settings → Secrets and
variables → Actions); otherwise it builds unsigned installers, as today.

**macOS** — Apple Developer Program (about US$99/year). Create a *Developer ID Application*
certificate, export it as `.p12`, and an App Store Connect API key for notarization.
- Variable `MACOS_SIGNING=true`
- Secrets `MACOS_CERT_P12` (`base64 -i cert.p12`), `MACOS_CERT_PASSWORD`, and either
  `APPLE_API_KEY_P8` (the .p8 contents), `APPLE_API_KEY_ID`, `APPLE_API_ISSUER`
  or `APPLE_ID`, `APPLE_APP_PASSWORD`, `APPLE_TEAM_ID`.
- `scripts/sign-macos.sh` signs every binary inside the app (hardened runtime,
  `packaging/macos/entitlements.plist`), then the `.dmg`, notarizes and staples it.

**Windows** — pick one with the variable `WINDOWS_SIGNING`:
- `signpath` — **free for open source** through the [SignPath Foundation](https://signpath.org/)
  (requires an OSI license in this repo and their approval). Secret `SIGNPATH_API_TOKEN`; variables
  `SIGNPATH_ORGANIZATION_ID`, `SIGNPATH_PROJECT_SLUG`, `SIGNPATH_SIGNING_POLICY_SLUG`. Signs the installer.
- `azure` — Azure Artifact Signing (formerly Trusted Signing, paid monthly; identity eligibility
  applies). Secrets `AZURE_TENANT_ID`, `AZURE_CLIENT_ID`, `AZURE_CLIENT_SECRET`; variables
  `AZURE_SIGNING_ENDPOINT`, `AZURE_SIGNING_ACCOUNT`, `AZURE_CERT_PROFILE`. Signs `Ujto.exe` and the installer.

Unsigned builds work, but macOS Gatekeeper and Windows SmartScreen warn on first launch. After a
release, set `"status": "available"` in the landing's `src/content/download.json` and the
dashboard's `src/content/desktop.json` (ujto-admin).

Only process media you have the right to use.
