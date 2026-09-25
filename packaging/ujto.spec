# -*- mode: python ; coding: utf-8 -*-
# Build: pyinstaller packaging/ujto.spec  (from the repo root; see scripts/build.sh)
import os
import sys

from PyInstaller.utils.hooks import collect_data_files, collect_submodules

ROOT = os.path.abspath(os.path.join(SPECPATH, ".."))  # noqa: F821 (SPECPATH is set by PyInstaller)
os.chdir(ROOT)
sys.path.insert(0, ROOT)
from ujto_desktop import __version__  # noqa: E402

datas = [(os.path.join(ROOT, "assets"), "assets")] + collect_data_files("imageio_ffmpeg")
if os.path.isdir("vendor"):
    datas.append((os.path.join(ROOT, "vendor"), "vendor"))  # bundled deno (JS runtime yt-dlp needs for YouTube)

icon = {"darwin": "build/icon.icns", "win32": "build/icon.ico"}.get(sys.platform)
icon = os.path.join(ROOT, icon) if icon else None

a = Analysis(
    [os.path.join(ROOT, "packaging", "launcher.py")],
    pathex=[ROOT],
    datas=datas,
    hiddenimports=collect_submodules("ujto_desktop"),
    excludes=["tkinter"],
)
pyz = PYZ(a.pure)
exe = EXE(
    pyz,
    a.scripts,
    [],
    exclude_binaries=True,
    name="Ujto",
    console=False,
    icon=icon,
    # macOS delivers ujto:// links as Apple Events; this turns them into argv at launch.
    argv_emulation=sys.platform == "darwin",
)
coll = COLLECT(exe, a.binaries, a.datas, name="Ujto")

if sys.platform == "darwin":
    app = BUNDLE(
        coll,
        name="Ujto.app",
        icon=icon,
        bundle_identifier="dev.jcampos.ujto",
        version=__version__,
        info_plist={
            "CFBundleDisplayName": "Ujtö̀",
            "CFBundleShortVersionString": __version__,
            "NSHighResolutionCapable": True,
            "LSMinimumSystemVersion": "12.0",
            "CFBundleURLTypes": [{"CFBundleURLName": "dev.jcampos.ujto", "CFBundleURLSchemes": ["ujto"]}],
        },
    )
