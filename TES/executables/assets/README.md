# Assets

Pre-built icon files for all platforms. **These are committed to the repo** — no manual
icon generation is required at build time. The build scripts reference them directly.

| File | Purpose | Sizes |
|---|---|---|
| `gametools.ico` | Windows multi-size icon | 16, 32, 48, 64, 128, 256 px |
| `gametools.icns` | macOS icon bundle | 16, 32, 128, 256, 512, 1024 px |

## Regenerating (only needed after the logo changes)

Source image: `TES/gametools_tes_logo.png`

```bash
# From repo root
pip install Pillow icnsutil
python3 TES/executables/assets/generate_assets.py
# Then commit both .ico and .icns
git add TES/executables/assets/gametools.ico TES/executables/assets/gametools.icns
git commit -m "Regenerate icon assets from updated logo"
```
