#!/usr/bin/env bash
# ─────────────────────────────────────────────────────────
#  Job Scout — One-shot installer (macOS / Linux)
# ─────────────────────────────────────────────────────────
set -e

echo ""
echo "  🔍  Job Scout — Installer"
echo "  ──────────────────────────"
echo ""

# 1. Python check
if ! command -v python3 &>/dev/null; then
  echo "  ❌  Python 3.10+ is required but not found."
  echo "  👉  Install it from https://www.python.org/downloads/"
  exit 1
fi

PY_VER=$(python3 -c 'import sys; print(f"{sys.version_info.major}.{sys.version_info.minor}")')
PY_MAJOR=$(echo $PY_VER | cut -d. -f1)
PY_MINOR=$(echo $PY_VER | cut -d. -f2)

if [ "$PY_MAJOR" -lt 3 ] || ([ "$PY_MAJOR" -eq 3 ] && [ "$PY_MINOR" -lt 10 ]); then
  echo "  ❌  Python $PY_VER found. Need 3.10+."
  exit 1
fi
echo "  ✓  Python $PY_VER"

# 2. Virtual environment
DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" && pwd )"
VENV="$DIR/.venv"

if [ ! -d "$VENV" ]; then
  echo "  →  Creating virtual environment…"
  python3 -m venv "$VENV"
fi
echo "  ✓  Virtual environment ready"

# 3. Install dependencies
echo "  →  Installing dependencies (this may take ~60 s)…"
"$VENV/bin/pip" install --quiet --upgrade pip
"$VENV/bin/pip" install --quiet -r "$DIR/requirements.txt"
echo "  ✓  Dependencies installed"

echo ""
echo "  ✅  Installation complete!"
echo ""
echo "  Start Job Scout with:  ./start.sh"
echo ""
