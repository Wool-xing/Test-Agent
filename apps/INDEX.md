# Apps — Distribution Layer

## Purpose

Self-contained applications that package Test-Agent for end users.
Each app is an**independent project**with its own build system, dependencies, and config.
Apps depend ON `runtime/` and `utils/`, never the reverse.

## Structure

```text
apps/
├── desktop/                 ← Electron desktop app (Windows / macOS / Linux)
│   electron/                ← Electron main + preload + IPC
│   scripts/                 ← Build scripts
│   pyinstaller/             ← Python backend packaging
│   package.json             ← Node dependencies
│   electron-builder.yml     ← Electron Builder config
│
└── mobile/                  ← Capacitor mobile app (iOS / Android)
    capacitor.config.json    ← Capacitor config
    package.json             ← Node dependencies

```text

## Rules

### What goes here

- Self-contained application projects
- Each with its own `package.json`, build config, and README
- Build scripts specific to that app

### What does NOT go here

- Shared business logic — goes in `runtime/` or `utils/`
- AI agent definitions — goes in `ai/`
- Deployment config templates — goes in `deploy/`
- Build artifacts (`out/`, `dist/`, `node_modules/`) — gitignored

### Adding a new app

1. Create directory: `apps/<name>/`
2. Add `README.md` explaining the app
3. Keep it self-contained (own build, own deps)
4. Update CI if needed (`ci/`)
