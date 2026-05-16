#!/bin/bash
# Build complete desktop release (macOS/Linux)
set -euo pipefail
cd "$(dirname "$0")/.."
echo "=== Building Python backend ==="
bash scripts/build-python.sh
echo "=== Building Web UI ==="
cd ../runtime/web && npm ci && npm run build && cd -
echo "=== Building Electron ==="
npm ci
npm run build:electron
echo "=== Packaging ==="
npx electron-builder --config electron-builder.yml
echo "=== Done ==="
