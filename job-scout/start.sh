#!/usr/bin/env bash
# ─────────────────────────────────────────────────────────
#  Job Scout — Start (macOS / Linux)
# ─────────────────────────────────────────────────────────
set -e

DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" && pwd )"
VENV="$DIR/.venv"

if [ ! -d "$VENV" ]; then
  echo "  ⚠  Run ./install.sh first."
  exit 1
fi

PORT="${PORT:-5000}"
echo ""
echo "  🔍  Starting Job Scout on http://localhost:$PORT"
echo "  Press Ctrl+C to stop."
echo ""

# Open browser after 1.5 s
(sleep 1.5 && open "http://localhost:$PORT" 2>/dev/null || xdg-open "http://localhost:$PORT" 2>/dev/null || true) &

PORT=$PORT "$VENV/bin/python" "$DIR/app.py"
