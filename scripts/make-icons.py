"""Generate build/icon.ico (Windows) and build/icon.icns (macOS, via iconutil) from assets/icon.png."""

import shutil
import subprocess
import sys
from pathlib import Path

from PIL import Image

root = Path(__file__).resolve().parent.parent
src = Image.open(root / "assets" / "icon.png").convert("RGBA")
build = root / "build"
build.mkdir(exist_ok=True)
src.save(build / "icon.ico", sizes=[(16, 16), (32, 32), (48, 48), (64, 64), (128, 128), (256, 256)])

if sys.platform == "darwin":
    iconset = build / "icon.iconset"
    shutil.rmtree(iconset, ignore_errors=True)
    iconset.mkdir()
    for size in (16, 32, 128, 256, 512):
        src.resize((size, size), Image.LANCZOS).save(iconset / f"icon_{size}x{size}.png")
        src.resize((size * 2, size * 2), Image.LANCZOS).save(iconset / f"icon_{size}x{size}@2x.png")
    subprocess.run(["iconutil", "-c", "icns", str(iconset), "-o", str(build / "icon.icns")], check=True)
print("icons written to", build)
