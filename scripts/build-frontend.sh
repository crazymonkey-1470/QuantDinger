#!/bin/bash
# ======================================================
# Sync a production frontend build into this repository.
#
# Vue source is not in this open-source tree. Clone your private repo
# elsewhere, build it, then either:
#   - export QUANTDINGER_VUE_SRC=/path/to/vue-repo && ./scripts/build-frontend.sh
#   - or manually: rsync -a --delete /path/to/vue-repo/dist/ frontend/dist/
#
# Usage:
#   QUANTDINGER_VUE_SRC=~/path/to/private-vue-repo ./scripts/build-frontend.sh
#
# Prerequisites:
#   - Node.js >= 16 in PATH (only when using this script to npm build)
# ======================================================

set -e

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(cd "$SCRIPT_DIR/.." && pwd)"
DIST_TARGET="$PROJECT_ROOT/frontend/dist"

echo "============================================"
echo "  QuantDinger — sync frontend dist"
echo "============================================"

if [ -z "${QUANTDINGER_VUE_SRC:-}" ] || [ ! -d "$QUANTDINGER_VUE_SRC" ]; then
  echo "ERROR: Set QUANTDINGER_VUE_SRC to the root of your private Vue repository clone."
  echo "Example: export QUANTDINGER_VUE_SRC=\$HOME/work/QuantDinger-Vue"
  exit 1
fi

VUE_DIR="$(cd "$QUANTDINGER_VUE_SRC" && pwd)"
echo "Vue repo: $VUE_DIR"

echo "[1/3] Installing dependencies..."
cd "$VUE_DIR"
npm install --legacy-peer-deps

echo "[2/3] Building production bundle..."
npm run build

echo "[3/3] Syncing dist -> frontend/dist/..."
rm -rf "$DIST_TARGET"/*
cp -r "$VUE_DIR/dist/"* "$DIST_TARGET/"

echo ""
echo "============================================"
echo "  Done. Output: frontend/dist/"
echo "  Files: $(find "$DIST_TARGET" -type f | wc -l)"
echo "  Size:  $(du -sh "$DIST_TARGET" | cut -f1)"
echo "============================================"
