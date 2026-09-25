"""JavaScript bridge exposed to the dashboard as window.pywebview.api.

The web app (fe/app, services/desktop.service.ts) calls it only when it runs inside this
window. The user's tokens never leave the web view: the web app asks the API for a presigned
S3 POST and hands it here; the bridge downloads the media on this machine (the user's own
connection, which YouTube accepts), uploads it with that form and deletes the local copy.
"""

from __future__ import annotations

import json
import logging
import os
import shutil
import tempfile
import threading
from pathlib import Path
from typing import Any, Callable
from urllib.parse import urlsplit

from . import config

log = logging.getLogger("ujto.bridge")


class Cancelled(Exception):
    """The user cancelled the job from the web app."""


def origin_of(url: str | None) -> str:
    parts = urlsplit(url or "")
    return f"{parts.scheme}://{parts.netloc}" if parts.scheme and parts.netloc else ""


def _is_public_http_url(url: str) -> bool:
    parts = urlsplit(url)
    return parts.scheme in ("http", "https") and bool(parts.netloc)


class Bridge:
    def __init__(self, window_provider: Callable[[], Any] | None = None):
        # The window is created after the bridge; resolve it lazily.
        self._window_provider = window_provider or (lambda: None)
        self._cancelled: set[str] = set()
        self._lock = threading.Lock()

    # ---- security ---------------------------------------------------------------------------
    def _ensure_trusted(self) -> None:
        """Refuse calls unless the window shows the Ujtö̀ dashboard (never another origin)."""
        window = self._window_provider()
        current = window.get_current_url() if window else None
        if origin_of(current) != config.APP_ORIGIN:
            raise PermissionError(f"Bridge refused for {origin_of(current) or 'unknown origin'}")

    # ---- progress ---------------------------------------------------------------------------
    def _progress(self, job_id: str, phase: str, fraction: float) -> None:
        window = self._window_provider()
        if not window:
            return
        script = "window.ujtoDesktop && window.ujtoDesktop.onProgress && window.ujtoDesktop.onProgress({}, {}, {})".format(
            json.dumps(job_id), json.dumps(phase), round(max(0.0, min(1.0, fraction)), 3)
        )
        try:
            window.evaluate_js(script)
        except Exception:  # the page may be navigating; progress is best effort
            pass

    def _check_cancel(self, job_id: str) -> None:
        with self._lock:
            if job_id in self._cancelled:
                raise Cancelled()

    # ---- API exposed to JavaScript ----------------------------------------------------------
    def version(self) -> str:
        return config.VERSION

    def capabilities(self) -> dict:
        """What this build can do; the web app hides on-device downloads when they're off."""
        return {"edition": config.EDITION, "download": config.DOWNLOADS_ENABLED}

    def probe(self, url: str) -> dict:
        """Title and duration of a link, without downloading it."""
        try:
            self._ensure_trusted()
            if not config.DOWNLOADS_ENABLED:
                return {"ok": False, "error": "NOT_AVAILABLE"}
            if not _is_public_http_url(url):
                return {"ok": False, "error": "INVALID_URL"}
            import yt_dlp

            with yt_dlp.YoutubeDL(self._ydl_options()) as ydl:
                info = ydl.extract_info(url, download=False)
            return {"ok": True, "title": info.get("title") or "", "duration": info.get("duration")}
        except PermissionError:
            raise
        except Exception as exc:
            log.warning("probe failed: %s", exc)
            return {"ok": False, "error": _short(exc)}

    def download_and_upload(self, job_id: str, url: str, upload: dict) -> dict:
        """Download the audio of `url`, POST it to the presigned S3 form, delete the local file."""
        self._ensure_trusted()
        if not config.DOWNLOADS_ENABLED:
            return {"ok": False, "error": "NOT_AVAILABLE"}
        if not _is_public_http_url(url):
            return {"ok": False, "error": "INVALID_URL"}
        if not (isinstance(upload, dict) and _is_public_http_url(upload.get("url", "")) and isinstance(upload.get("fields"), dict)):
            return {"ok": False, "error": "INVALID_UPLOAD"}
        work_dir = Path(tempfile.mkdtemp(prefix="ujto-"))
        try:
            audio = self._download(job_id, url, work_dir)
            self._check_cancel(job_id)
            self._upload(job_id, audio, upload)
            self._progress(job_id, "done", 1.0)
            return {"ok": True}
        except Cancelled:
            return {"ok": False, "error": "UPLOAD_CANCELLED"}
        except Exception as exc:
            log.exception("job %s failed", job_id)
            return {"ok": False, "error": _short(exc)}
        finally:
            shutil.rmtree(work_dir, ignore_errors=True)
            with self._lock:
                self._cancelled.discard(job_id)

    def cancel(self, job_id: str) -> None:
        with self._lock:
            self._cancelled.add(job_id)

    # ---- internals --------------------------------------------------------------------------
    def _ydl_options(self) -> dict:
        import imageio_ffmpeg

        options: dict[str, Any] = {
            "quiet": True,
            "noprogress": True,
            "no_warnings": True,
            "noplaylist": True,
            "ffmpeg_location": imageio_ffmpeg.get_ffmpeg_exe(),
        }
        deno = config.bundled_deno()
        if deno:
            options["js_runtimes"] = {"deno": {"path": deno}}
        return options

    def _download(self, job_id: str, url: str, work_dir: Path) -> Path:
        import yt_dlp

        def hook(d: dict) -> None:
            self._check_cancel(job_id)
            if d.get("status") == "downloading":
                total = d.get("total_bytes") or d.get("total_bytes_estimate") or 0
                if total:
                    self._progress(job_id, "downloading", d.get("downloaded_bytes", 0) / total)

        options = self._ydl_options() | {
            "format": "bestaudio/best",
            "outtmpl": str(work_dir / "audio.%(ext)s"),
            "progress_hooks": [hook],
            # Audio only, re-encoded to m4a (AAC): small uploads, decoded fine by the worker.
            "postprocessors": [{"key": "FFmpegExtractAudio", "preferredcodec": "m4a", "preferredquality": "96"}],
        }
        self._progress(job_id, "downloading", 0.0)
        with yt_dlp.YoutubeDL(options) as ydl:
            ydl.download([url])
        files = sorted(work_dir.glob("audio.*"))
        if not files:
            raise RuntimeError("DOWNLOAD_FAILED")
        return files[0]

    def _upload(self, job_id: str, path: Path, upload: dict) -> None:
        import requests
        from requests_toolbelt import MultipartEncoder, MultipartEncoderMonitor

        size = path.stat().st_size
        if size > config.MAX_UPLOAD_BYTES:
            raise RuntimeError("FILE_TOO_LARGE")
        with path.open("rb") as fh:
            fields = list(upload["fields"].items()) + [("file", ("audio.m4a", fh, upload["fields"].get("Content-Type", "audio/mp4")))]
            encoder = MultipartEncoder(fields=fields)

            def on_chunk(monitor: MultipartEncoderMonitor) -> None:
                self._check_cancel(job_id)
                self._progress(job_id, "uploading", monitor.bytes_read / max(1, monitor.len))

            monitor = MultipartEncoderMonitor(encoder, on_chunk)
            response = requests.post(upload["url"], data=monitor, headers={"Content-Type": monitor.content_type}, timeout=600)
        if response.status_code >= 300:
            raise RuntimeError(f"UPLOAD_FAILED ({response.status_code})")


def _short(exc: Exception) -> str:
    text = str(exc).strip().splitlines()[-1] if str(exc).strip() else exc.__class__.__name__
    return text[:300]


def ffmpeg_available() -> bool:
    try:
        import imageio_ffmpeg

        return os.path.exists(imageio_ffmpeg.get_ffmpeg_exe())
    except Exception:
        return False
