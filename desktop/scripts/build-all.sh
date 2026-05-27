#!/bin/bash
# Build complete desktop release (macOS/Linux)
set -euo pipefail
cd "$(dirname "$0")/.."
echo "=== Building Python backend ==="
bash scripts/build-python.sh
echo "=== Building Web UI ==="
WEB_DIR="../runtime/web"
if [ -f "$WEB_DIR/package.json" ]; then
  (cd "$WEB_DIR" && npm ci && npm run build)
else
  echo "  (skip: $WEB_DIR/package.json not found)"
fi
echo "=== Building Electron ==="
npm ci
npm run build:electron
echo "=== Packaging ==="
npx electron-builder --config electron-builder.yml
echo "=== Done ==="
