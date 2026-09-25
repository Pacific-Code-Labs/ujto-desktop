"""Settings. UJTO_APP_URL points the window at another dashboard (e.g. http://localhost:5174)."""

import os
import sys
from pathlib import Path
from urllib.parse import urlsplit

from . import __version__

APP_URL = os.getenv("UJTO_APP_URL", "https://app.ujto.jcampos.dev").rstrip("/")
APP_ORIGIN = "{0.scheme}://{0.netloc}".format(urlsplit(APP_URL))
RELEASES_API = "https://api.github.com/repos/Pacific-Code-Labs/ujto-desktop/releases/latest"
RELEASES_PAGE = "https://github.com/Pacific-Code-Labs/ujto-desktop/releases/latest"
URL_SCHEME = "ujto"
VERSION = __version__

# Largest file the bridge will upload; the presigned POST enforces the user's plan limit anyway.
MAX_UPLOAD_BYTES = 2 * 1024 * 1024 * 1024


def resource_dir() -> Path:
    """Folder with bundled files (PyInstaller's _MEIPASS when frozen, the repo otherwise)."""
    return Path(getattr(sys, "_MEIPASS", Path(__file__).resolve().parent.parent))


def data_dir() -> Path:
    """Per-user folder for the web view's storage (keeps the Cognito session between runs)."""
    if sys.platform == "darwin":
        base = Path.home() / "Library" / "Application Support"
    elif sys.platform == "win32":
        base = Path(os.getenv("APPDATA", Path.home() / "AppData" / "Roaming"))
    else:
        base = Path(os.getenv("XDG_DATA_HOME", Path.home() / ".local" / "share"))
    path = base / "Ujto"
    path.mkdir(parents=True, exist_ok=True)
    return path


def bundled_deno() -> str | None:
    """Deno shipped inside the app (yt-dlp needs a JS runtime for YouTube); else PATH lookup."""
    name = "deno.exe" if sys.platform == "win32" else "deno"
    candidate = resource_dir() / "vendor" / name
    return str(candidate) if candidate.exists() else None
