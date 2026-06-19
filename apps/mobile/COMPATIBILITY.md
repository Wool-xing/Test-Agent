# Test-Agent 兼容性矩阵

## 桌面版 (Electron + PyInstaller)

| 操作系统 | 版本 | 架构 | 状态 |
| ---------- | ------ | ------ | ------ |
| Windows 11 | 21H2+ | x64 | 完整支持 |
| Windows 10 | 21H2+ | x64 | 完整支持 |
| Windows 10 | 1809-21H1 | x64 | 支持 (无 WebView2 需系统自带) |
| Windows 7/8/8.1 | — | — | **不支持** |
| macOS 15 Sequoia | 15.0+ | arm64, x64 | 完整支持 |
| macOS 14 Sonoma | 14.0+ | arm64, x64 | 完整支持 |
| macOS 13 Ventura | 13.0+ | arm64, x64 | 支持 |
| macOS 12 Monterey | 12.0+ | x64 | 支持 (仅 x64) |
| Linux (AppImage) | Ubuntu 22.04+ / Debian 12+ | x64 | 支持 |

## 移动版 (PWA + Capacitor)

| 平台 | 最低版本 | 安装方式 |
| ------ | ---------- | --------- |
| iOS | 14.0+ | App Store / PWA "添加到主屏幕" |
| iPadOS | 14.0+ | App Store / PWA |
| Android | 8.0 (API 26)+ | Google Play / PWA "安装" |
| Android Go | 12+ | PWA (lite) |
| ChromeOS | 91+ | Google Play / PWA |

## 浏览器 (Web UI)

| 浏览器 | 最低版本 | 备注 |
| -------- | ---------- | ------ |
| Chrome | 90+ | 完整支持 |
| Firefox | 90+ | 完整支持 |
| Safari | 15+ | PWA + 添加到主屏幕 |
| Edge | 90+ | 完整支持 |
| Samsung Internet | 16+ | 支持 |
| Opera | 76+ | 支持 |

## 后端 (Python Runtime)

| 环境 | 最低版本 |
| ------ | ---------- |
| Python | 3.10+ (推荐 3.11) |
| PostgreSQL | 14+ (可选，stub 模式不需要) |
| Docker | 24+ (可选) |
| Node.js | 18+ (仅 Web UI 开发需要) |

## 屏幕适配

| 设备 | 宽度 | 布局 |
| ------ | ------ | ------ |
| 手机 | < 640px | 单列，底部导航 |
| 平板 | 640-1024px | 双列 |
| 桌面 | > 1024px | 完整布局 |
| 超大屏 | > 1536px | 宽屏优化 |
