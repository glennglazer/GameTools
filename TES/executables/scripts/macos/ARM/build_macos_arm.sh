#!/usr/bin/env bash
# GameTools TES — macOS Apple Silicon (ARM) build script
# Run from repo root: bash TES/executables/scripts/macos/ARM/build_macos_arm.sh
# Requirements: Python 3.11+ (arm64), pip, Nuitka, create-dmg
#   brew install create-dmg

set -euo pipefail

VERSION="${1:-1.0.0}"
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
REPO_ROOT="$(cd "$SCRIPT_DIR/../../../../.." && pwd)"
SRC_DIR="$REPO_ROOT/TES/executables/src"
DIST_DIR="$REPO_ROOT/TES/executables/dist/macos/ARM"
BUILD_TMP="$(mktemp -d)"

# Ensure we're building native ARM64
PYTHON="python3"

echo "=== GameTools TES macOS ARM (Apple Silicon) Build v$VERSION ==="
echo "Arch:  $(uname -m)"
echo "Repo:  $REPO_ROOT"

# ── 1. Install dependencies ────────────────────────────────────────────────
echo ""
echo "[1/5] Installing Python dependencies..."
$PYTHON -m pip install -r "$SRC_DIR/requirements.txt" nuitka zstandard --quiet

# ── 2. Compile with Nuitka ─────────────────────────────────────────────────
echo ""
echo "[2/5] Compiling with Nuitka (standalone onefile, arm64)..."

$PYTHON -m nuitka \
  --onefile \
  --standalone \
  --macos-create-app-bundle \
  --macos-app-name="GameTools TES" \
  --macos-app-version="$VERSION" \
  --macos-app-icon="$REPO_ROOT/TES/executables/assets/gametools.icns" \
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
codesign --deep --force --sign "-" "$APP_BUNDLE" || true

# ── 4. Create DMG ─────────────────────────────────────────────────────────
echo ""
echo "[4/5] Creating DMG..."
mkdir -p "$DIST_DIR"
DMG_PATH="$DIST_DIR/GameTools_TES_${VERSION}_ARM.dmg"

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
  hdiutil create -volname "GameTools TES" -srcfolder "$APP_BUNDLE" \
    -ov -format UDZO "$DMG_PATH"
fi

# ── 5. Verify ──────────────────────────────────────────────────────────────
echo ""
echo "[5/5] Artifacts in $DIST_DIR:"
ls -lh "$DIST_DIR"

echo ""
echo "=== Build complete! ==="
echo "NOTE: Ad-hoc signed. First launch: right-click → Open, or"
echo "      System Settings → Privacy & Security → Allow."
