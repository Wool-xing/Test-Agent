# Test-Agent Desktop

Cross-platform desktop GUI wrapping the [Test-Agent](https://github.com/Wool-xing/Test-Agent) testing framework.

## Architecture

```
Electron Shell (main.ts)
  ├── spawns Python backend (tagent-backend)
  │     └── FastAPI on localhost:8800
  └── loads React Web UI (runtime/web/dist/)
        └── HTTP calls to backend
```

## Dev

```bash
# Terminal 1: start Python backend
uvicorn runtime.api.main:app --port 8800

# Terminal 2: start Vite dev server
cd runtime/web && npm run dev

# Terminal 3: start Electron (loads from Vite dev server)
cd desktop && npm run dev
```

## Build

```bash
# 1. Build Python backend
pip install pyinstaller
bash scripts/build-python.sh     # macOS/Linux
powershell scripts/build-python.ps1  # Windows

# 2. Full build (Python + Web UI + Electron + package)
bash scripts/build-all.sh
```

## Release Artifacts

- **Windows**: `Test-Agent-Setup-{version}.exe` (NSIS installer)
- **macOS**: `Test-Agent-{version}.dmg`
- **Linux**: `Test-Agent-{version}.AppImage`

CI/CD builds on tag push (`v*`) via `.github/workflows/desktop-release.yml`.
