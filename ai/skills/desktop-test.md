---
name: desktop-test
description: 桌面应用测试 Skill。Windows EXE / macOS .app / Linux GUI / Electron 应用。底层调用 utils/desktop_driver。
tools: Read, Write, Bash, Grep, Glob
SKILL_IMPL_STATUS: script
---

# 桌面应用测试 Skill

## 触发方式

```text
/desktop-test [应用路径 或 应用描述]

```text

## 🔔 开测前准备清单（必看）

调用本 skill 前确认：

```text

□ 应用路径 → .env WIN_APP_PATH / MAC_APP_PATH / ELECTRON_APP_PATH
□ 操作系统匹配（Windows EXE 必须 Win，macOS .app 必须 Mac）
□ pip 装：pywinauto+uiautomation（Win）/ pyautogui（mac/linux）/ playwright（Electron）
□ 应用版本号（Bug 报告 buildFound 用）
□ 测试账号（如应用需登录）
□ EXE+WS 混合：WS_URL → .env

```text

缺任一项告诉 test-lead，会路由 env-manager 协助配置。

## 适用场景

- Windows .exe 原生应用（WPF / WinForms / Win32 / Qt）
- macOS .app（Cocoa）
- Linux GUI（GTK / Qt）
- Electron 跨平台应用（VSCode / 钉钉 PC / 飞书 PC / IM）
-**EXE + WebSocket 协议**混合（IM、交易终端、远程协同等）—— UI 层 + 协议层双层验证（详见 11-桌面测试.md "EXE + WebSocket 协议混合测试"段）

## 执行流程

### Step 1：环境检查

```bash

# Windows

python -c "import pywinauto; print(pywinauto.__version__)"

# macOS

python -c "import pyautogui; print(pyautogui.__version__)"
osascript -e 'tell application "System Events" to keystroke ""'

# Electron（需 Playwright）

playwright --version

```text

### Step 2：启动应用 + 创建 driver

由 `desktop-tester` agent 调 `utils/desktop_driver` 工厂方法生成。

### Step 3：执行测试

```bash

# Windows

pytest -m "desktop and windows and p0" -v

# macOS

pytest -m "desktop and macos and p0" -v

# Electron 跨平台

pytest -m "desktop and electron" -v

# EXE + WebSocket 协议混合

pytest -m "desktop and (websocket or ws)" -v

# 仅 WS 协议层（不经 UI，速度快）

pytest -m "websocket" -v

```text

WS 一键性能：

```bash

python -m utils.websocket_helper load \
    --url ws://server.example.com/socket \
    --count 1000 --messages 10

```text

### Step 4：进程性能采集（可选）

```bash

python -m utils.desktop_driver collect-perf \
    --pid <PID> --duration 60 \
    --output workspace/测试报告/{项目名}/desktop-perf/

```text

## 质量门禁

| 指标 | 要求 |
| ------ | ------ |
| P0 用例通过率 | ≥95% |
| 启动时间（冷） | < 5s（视应用复杂度） |
| 内存峰值 | 业务约定 |
| 崩溃率 | < 0.1% |

## 跨平台 CI（GitHub Actions matrix）

```yaml

strategy:
  matrix:
    os: [windows-latest, macos-latest, ubuntu-latest]
runs-on: ${{ matrix.os }}
steps:

  - run: pytest -m "desktop and p0"

```text

## 输出文件

```text

workspace/
├── 自动化脚本/python/desktop/{windows,macos,electron}/
└── 测试报告/
    ├── desktop-screenshots/
    ├── desktop-perf/
    ├── win-event-log/
    └── mac-console/

```text
