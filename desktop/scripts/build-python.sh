#!/bin/bash
# Build Python backend with PyInstaller (macOS/Linux)
set -euo pipefail
cd "$(dirname "$0")/.."
echo "Building Python backend..."
pip install pyinstaller -q
pyinstaller --clean --noconfirm pyinstaller/tagent_backend.spec
echo "Backend built: dist-python/tagent-backend"
