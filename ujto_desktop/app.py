"""Native window showing the Ujtö̀ dashboard, with the download bridge attached."""

from __future__ import annotations

import json
import logging
import sys
import threading
import urllib.request
import webbrowser
from urllib.parse import parse_qs, quote, urlsplit

import webview

from . import config
from .bridge import Bridge, origin_of

log = logging.getLogger("ujto")


def start_url(argv: list[str]) -> str:
    """Dashboard URL to open; a ujto://new?url=… deep link opens the New page with that link."""
    target = f"{config.APP_URL}/?client=desktop"
    link = next((a for a in argv[1:] if a.startswith(f"{config.URL_SCHEME}://")), None)
    if link:
        parts = urlsplit(link)
        shared = parse_qs(parts.query).get("url", [""])[0]
        page = (parts.netloc + parts.path).strip("/") or "new"
        if page == "new" and shared.startswith(("http://", "https://")):
            target = f"{config.APP_URL}/en/new?client=desktop&url={quote(shared, safe='')}"
    return target


def _keep_on_dashboard(window: webview.Window) -> None:
    """Links to other sites open in the system browser; the window stays on the dashboard."""
    current = window.get_current_url() or ""
    if current and origin_of(current) != config.APP_ORIGIN and not current.startswith("about:"):
        log.info("leaving window for external %s", current)
        webbrowser.open(current)
        window.load_url(f"{config.APP_URL}/?client=desktop")


def _check_for_update(window: webview.Window) -> None:
    try:
        with urllib.request.urlopen(config.RELEASES_API, timeout=8) as res:
            latest = json.load(res).get("tag_name", "").lstrip("v")
    except Exception:
        return
    if latest and _version_tuple(latest) > _version_tuple(config.VERSION):
        title = "Ujtö̀"
        message = f"Ujtö̀ {latest} is available (you have {config.VERSION}). Download it now?\n\nUjtö̀ {latest} está disponible. ¿Descargarla ahora?"
        if window.create_confirmation_dialog(title, message):
            webbrowser.open(config.RELEASES_PAGE)


def _version_tuple(v: str) -> tuple[int, ...]:
    return tuple(int(p) for p in v.split(".") if p.isdigit())


def main(argv: list[str] | None = None) -> None:
    argv = argv if argv is not None else sys.argv
    logging.basicConfig(level=logging.INFO, format="%(asctime)s %(name)s %(levelname)s %(message)s")
    holder: dict[str, webview.Window] = {}
    bridge = Bridge(lambda: holder.get("window"))
    window = webview.create_window(
        "Ujtö̀",
        start_url(argv),
        js_api=bridge,
        width=1280,
        height=840,
        min_size=(420, 600),
        background_color="#1B1E26",
        text_select=True,
    )
    holder["window"] = window
    window.events.loaded += lambda: _keep_on_dashboard(window)

    def on_start() -> None:
        # Store builds are updated by the Microsoft Store; GitHub builds check their releases.
        if config.UPDATE_CHECK_ENABLED:
            threading.Thread(target=_check_for_update, args=(window,), daemon=True).start()

    # private_mode=False + a storage path keeps the sign-in between launches.
    webview.start(on_start, private_mode=False, storage_path=str(config.data_dir()), icon=str(config.resource_dir() / "assets" / "icon.png"))


if __name__ == "__main__":
    main()
