#!/usr/bin/env bash
# GameTools TES — macOS Intel build script
# Run from repo root: bash TES/executables/scripts/macos/intel/build_macos_intel.sh
# Requirements: Python 3.11+ (x86_64), pip, Nuitka, create-dmg
#   brew install create-dmg

set -euo pipefail

VERSION="${1:-1.0.0}"
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
REPO_ROOT="$(cd "$SCRIPT_DIR/../../../../.." && pwd)"
SRC_DIR="$REPO_ROOT/TES/executables/src"
DIST_DIR="$REPO_ROOT/TES/executables/dist/macos/intel"
BUILD_TMP="$(mktemp -d)"

PYTHON="python3"
# On Apple Silicon / rosetta — force x86_64 arch if needed:
# PYTHON="arch -x86_64 python3"

echo "=== GameTools TES macOS Intel Build v$VERSION ==="
echo "Repo:  $REPO_ROOT"
echo "Src:   $SRC_DIR"
echo "Dist:  $DIST_DIR"
echo "Tmp:   $BUILD_TMP"

# ── 1. Install dependencies ────────────────────────────────────────────────
echo ""
echo "[1/5] Installing Python dependencies..."
$PYTHON -m pip install -r "$SRC_DIR/requirements.txt" nuitka zstandard --quiet

# ── 2. Compile with Nuitka ─────────────────────────────────────────────────
echo ""
echo "[2/5] Compiling with Nuitka (standalone onefile)..."

$PYTHON -m nuitka \
  --standalone \
  --macos-create-app-bundle \
  --macos-app-name="GameTools TES" \
  --macos-app-version="$VERSION" \
  --include-data-dir="$SRC_DIR/ui=ui" \
  --include-data-dir="$REPO_ROOT/TES/mcp=rag" \
  --include-data-files="$REPO_ROOT/TES/database/gametools.sqlite3=data/gametools.sqlite3" \
  --output-filename="GameToolsTES" \
  --output-dir="$BUILD_TMP" \
  --assume-yes-for-downloads \
  --enable-plugin=anti-bloat \
  --nofollow-import-to=tkinter,unittest,email.mime,xml.etree \
  "$SRC_DIR/main.py"

APP_BUNDLE="$BUILD_TMP/GameToolsTES.app"

# ── 3. Code sign (ad-hoc) ─────────────────────────────────────────────────
echo ""
echo "[3/5] Code signing (ad-hoc)..."
# Ad-hoc signing allows the app to run locally without a paid Apple Developer account.
# Users need to approve in System Settings → Privacy & Security on first launch.
# For distribution, replace '-' with your Developer ID:
#   codesign --deep --force --options runtime \
#             --sign "Developer ID Application: Your Name (TEAMID)" "$APP_BUNDLE"
codesign --deep --force --sign "-" "$APP_BUNDLE" || true

# ── 4. Create DMG ─────────────────────────────────────────────────────────
echo ""
echo "[4/5] Creating DMG..."
mkdir -p "$DIST_DIR"
DMG_PATH="$DIST_DIR/GameTools_TES_${VERSION}_Intel.dmg"

if command -v create-dmg &>/dev/null; then
  create-dmg \
    --volname "GameTools TES" \
    --volicon "$REPO_ROOT/TES/executables/assets/gametools.icns" \
    --window-size 540 360 \
    --icon-size 128 \
    --icon "GameToolsTES.app" 140 180 \
    --app-drop-link 400 180 \
    --hide-extension "GameToolsTES.app" \
    "$DMG_PATH" \
    "$APP_BUNDLE" || true
else
  # Fallback: plain hdiutil DMG
  hdiutil create -volname "GameTools TES" -srcfolder "$APP_BUNDLE" \
    -ov -format UDZO "$DMG_PATH"
fi

# ── 5. Verify ──────────────────────────────────────────────────────────────
echo ""
echo "[5/5] Artifacts in $DIST_DIR:"
ls -lh "$DIST_DIR"

echo ""
echo "=== Build complete! ==="
echo "DMG: $DMG_PATH"
echo ""
echo "NOTE: The app is signed ad-hoc. On first launch, right-click → Open,"
echo "      or go to System Settings → Privacy & Security → Allow."
echo "      For a fully trusted build, sign with a Developer ID certificate."
