"""Generate gametools.ico (Windows) and gametools.icns (macOS) from the logo PNG.

Run from the repo root or from this directory:
    python3 TES/executables/assets/generate_assets.py

Requirements: Pillow, icnsutil
    pip install Pillow icnsutil

The source image is TES/gametools_tes_logo.png.
Outputs: gametools.ico and gametools.icns in the same directory as this script.
"""
import sys
from pathlib import Path

try:
    from PIL import Image
except ImportError:
    sys.exit("Pillow is required: pip install Pillow")

try:
    import icnsutil
except ImportError:
    sys.exit("icnsutil is required: pip install icnsutil")

SCRIPT_DIR = Path(__file__).resolve().parent
REPO_ROOT   = SCRIPT_DIR.parent.parent.parent   # TES/executables/assets → TES/executables → TES → GameTools
LOGO_PATH   = REPO_ROOT / "TES" / "gametools_tes_logo.png"

if not LOGO_PATH.exists():
    sys.exit(f"Logo not found at {LOGO_PATH}")

print(f"Source: {LOGO_PATH}")

# ── Load and normalise to RGBA ───────────────────────────────────────────────

orig = Image.open(LOGO_PATH).convert("RGBA")
print(f"Loaded: {orig.size[0]}×{orig.size[1]} px, mode={orig.mode}")


def _make_square(img: Image.Image, size: int) -> Image.Image:
    """Resize to a square of given pixel size using high-quality resampling."""
    return img.resize((size, size), Image.LANCZOS)


# ── Windows .ico ─────────────────────────────────────────────────────────────
# Standard sizes for a Windows application icon.
# Pillow's ICO plugin: pass `sizes` as a list of (w,h) tuples and it
# auto-resamples from the source image and embeds all sizes in one file.
ICO_SIZES = [(16, 16), (32, 32), (48, 48), (64, 64), (128, 128), (256, 256)]

ico_path = SCRIPT_DIR / "gametools.ico"
orig.save(ico_path, format="ICO", sizes=ICO_SIZES)
import struct
with open(ico_path, "rb") as fh:
    n = struct.unpack_from("<H", fh.read(6), 4)[0]
print(f"Written: {ico_path}  ({ico_path.stat().st_size // 1024} KB, {n} sizes embedded)")


# ── macOS .icns ───────────────────────────────────────────────────────────────
# icnsutil guesses the icns type from the image dimensions in the PNG data.
# Sizes: 16, 32, 128, 256, 512 → standard icons; 1024 → treated as 512@2x (retina).
ICNS_SIZES = [16, 32, 128, 256, 512, 1024]

import io
import tempfile, os

icns_img = icnsutil.IcnsFile()
with tempfile.TemporaryDirectory() as tmp:
    for s in ICNS_SIZES:
        resized = _make_square(orig, s)
        buf = io.BytesIO()
        resized.save(buf, format="PNG")
        png_bytes = buf.getvalue()
        # Write to a temp file so icnsutil can sniff extension + size
        tmp_path = os.path.join(tmp, f"icon_{s}x{s}.png")
        with open(tmp_path, "wb") as fh:
            fh.write(png_bytes)
        icns_img.add_media(file=tmp_path)

icns_path = SCRIPT_DIR / "gametools.icns"
icns_img.write(str(icns_path))
print(f"Written: {icns_path}  ({icns_path.stat().st_size // 1024} KB)")

print("Done.")
