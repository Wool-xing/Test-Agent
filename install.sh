#!/usr/bin/env bash
# Test-Agent V2.0.0 — one-command install (Linux / macOS)
set -euo pipefail

RED='\033[0;31m'; GREEN='\033[0;32m'; CYAN='\033[0;36m'; NC='\033[0m'
echo -e "${CYAN}Test-Agent V2.0.0 — Install${NC}"

# Detect Python
PYTHON=""
for cmd in python3 python; do
    if command -v "$cmd" &>/dev/null; then
        ver=$("$cmd" -c "import sys; print(f'{sys.version_info.major}.{sys.version_info.minor}')")
        major=$("$cmd" -c "import sys; print(sys.version_info.major)")
        if [ "$major" -ge 3 ]; then
            PYTHON="$cmd"; echo -e "  ${GREEN}Python $ver ($cmd)${NC}"; break
        fi
    fi
done
if [ -z "$PYTHON" ]; then
    echo -e "${RED}Python >= 3.10 required. Install from https://python.org${NC}"; exit 1
fi

# Install
echo -e "\nInstalling dependencies..."
"$PYTHON" -m pip install --upgrade pip -q
"$PYTHON" -m pip install -r requirements/base.txt -q 2>/dev/null || "$PYTHON" -m pip install -e . -q 2>/dev/null || true

# Quick test
echo -e "\nVerifying..."
"$PYTHON" -m runtime.cli.main --version 2>/dev/null || "$PYTHON" -c "from runtime import __version__; print(f'Test-Agent v{__version__}')"

echo -e "\n${GREEN}Install complete.${NC}"
echo -e "Next: ${CYAN}tagent init${NC} or see STARTUP.md"
