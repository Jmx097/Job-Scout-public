#!/usr/bin/env bash
# ─────────────────────────────────────────────────────────
#  Job Scout — Build one-click binary (macOS / Linux)
#  Produces: dist/JobScout
# ─────────────────────────────────────────────────────────
set -e

DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" && pwd )"
VENV="$DIR/.venv"

echo ""
echo "  🔨  Job Scout — Build Executable"
echo "  ──────────────────────────────────"
echo ""

if [ ! -d "$VENV" ]; then
  echo "  ⚠  Run ./install.sh first."; exit 1
fi

# 1. Install build deps
echo "  →  Installing PyInstaller + Pillow…"
"$VENV/bin/pip" install --quiet pyinstaller pillow
echo "  ✓  Build tools ready"

# 2. Generate icon (produces icon.ico; also used as .icns on Mac via pyinstaller)
echo "  →  Generating icon…"
"$VENV/bin/python" "$DIR/make_icon.py"

# 3. Clean
rm -rf "$DIR/dist" "$DIR/build"

# 4. Build
echo "  →  Building executable (1-3 minutes)…"
"$VENV/bin/pyinstaller" "$DIR/JobScout.spec" \
  --distpath "$DIR/dist" \
  --workpath "$DIR/build" \
  --noconfirm

echo ""
echo "  ✅  Build complete!"
echo ""
echo "  Executable: dist/JobScout"
echo "  Double-click it (or run ./dist/JobScout) to launch."
echo ""

# macOS: wrap in .app if possible
if [[ "$OSTYPE" == "darwin"* ]] && [ -f "$DIR/dist/JobScout" ]; then
  APP="$DIR/dist/JobScout.app"
  mkdir -p "$APP/Contents/MacOS"
  cp "$DIR/dist/JobScout" "$APP/Contents/MacOS/JobScout"
  cat > "$APP/Contents/Info.plist" <<PLIST
<?xml version="1.0" encoding="UTF-8"?>
<!DOCTYPE plist PUBLIC "-//Apple//DTD PLIST 1.0//EN" "http://www.apple.com/DTDs/PropertyList-1.0.dtd">
<plist version="1.0"><dict>
  <key>CFBundleName</key><string>JobScout</string>
  <key>CFBundleExecutable</key><string>JobScout</string>
  <key>CFBundleIdentifier</key><string>com.jobscout.app</string>
  <key>CFBundleVersion</key><string>1.0</string>
  <key>CFBundlePackageType</key><string>APPL</string>
  <key>LSUIElement</key><false/>
</dict></plist>
PLIST
  echo "  macOS .app bundle: dist/JobScout.app"
fi
