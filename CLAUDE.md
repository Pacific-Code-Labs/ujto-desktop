# ujto-desktop (fe/desktop)

- Public repo. No secrets: the app only loads the public dashboard URL and uses presigned uploads
  the web app obtains with the user's own session.
- The UI is the deployed dashboard (fe/app); do NOT build UI here. Desktop-only abilities go in
  `ujto_desktop/bridge.py` and are called from fe/app `services/desktop.service.ts` — change both
  together (method names, arguments, the `window.ujtoDesktop.onProgress` contract).
- Keep the origin check in `Bridge._ensure_trusted` and temp cleanup in `finally`.
- Asset names in `.github/workflows/release.yml`/`scripts/build.sh` are referenced by the landing and
  dashboard content (`download.json`, `desktop.json`): never rename them.
- Release = push a tag `vX.Y.Z` (match `ujto_desktop.__version__`). The workflow builds the 4
  platforms, creates the GitHub release, and the `downloads` job publishes the installers to the
  media CDN: `https://media.ujto.jcampos.dev/downloads/desktop/{vX.Y.Z,latest}/<asset>` (+
  `latest/version.json`). The sites link to `latest/`. Its OIDC role (secret
  `AWS_DOWNLOADS_ROLE_ARN`, from ujto-public-be `deploy-desktop-downloads-role.sh`) works only for
  tags and may only write `downloads/desktop/*`. Builds are unsigned until signing is configured
  (Gatekeeper / SmartScreen warnings).
- Verify: `.venv/bin/python -m pytest -q tests`; `bash scripts/build.sh` on macOS for a local .app.
- Two editions (`UJTO_EDITION`, `config.EDITION`): `full` (downloads + update check) and `store`
  (Microsoft Store: no yt-dlp/ffmpeg/Deno in the bundle; `capabilities().download` is false). Any new
  downloader-type feature must stay out of the store edition.
- MSIX: `scripts/build-msix.ps1` + `packaging/windows/msix/AppxManifest.xml`; the Identity values must
  match Partner Center exactly (repo variables `MSSTORE_*`).
