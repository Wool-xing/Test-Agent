# Test-Agent 全平台上架指南

覆盖: Windows .exe | macOS .dmg | iOS App Store | Android Google Play | PWA

---

## 一、Windows .exe (NSIS 安装包)

### 前置

- Windows 10/11 x64, Python 3.11, Node.js 20, Git
- GitHub Actions 自动编译 (推荐), 或本地编译

### 自动发布 (CI)

```bash
git tag v1.0.0 && git push origin v1.0.0
```

等待 ~12 分钟 → GitHub Releases 自动出现 `.exe`

### 手动本地编译

```powershell
# 1. 编译 Python 后端
pip install pyinstaller
pyinstaller --clean --noconfirm desktop/pyinstaller/tagent_backend.spec
# → dist-python/tagent-backend.exe

# 2. 编译 Web 前端
cd runtime/web
npm install && npm run build
# → dist/

# 3. 编译 Electron + 打包
cd ../../desktop
npm install
npx tsc -p electron/tsconfig.json
npx electron-builder --win
# → dist-electron/Test-Agent.Setup.X.X.X.exe
```

### 上架渠道

| 渠道 | 操作 |
|------|------|
| **GitHub Releases** | 拖入 `.exe` 发布 |
| **官网下载页** | 托管 `.exe` 直链 |
| **Microsoft Store** | 用 MSIX Packaging Tool 转换 `.exe` → `.msix`，提交 Partner Center |

### 兼容性

- Windows 10 21H2+ / Windows 11
- x64 架构
- 安装后约 300MB

---

## 二、macOS .dmg

### 前置

- macOS 12+, Xcode 16+, Apple Developer 账号 ($99/年, 签名用)
- 同 CI 自动或本地编译

### 自动发布 (CI)

```bash
git tag v1.0.0 && git push origin v1.0.0
```

### 手动本地编译

```bash
# 1. 编译 Python 后端
pip install pyinstaller
pyinstaller --clean --noconfirm desktop/pyinstaller/tagent_backend.spec
# → dist-python/tagent-backend

# 2. 编译 Web 前端
cd runtime/web && npm install && npm run build

# 3. 编译 Electron + 打包
cd ../../desktop && npm install
npx tsc -p electron/tsconfig.json
npx electron-builder --mac
# → dist-electron/Test-Agent-X.X.X.dmg (Intel)
# → dist-electron/Test-Agent-X.X.X-arm64.dmg (Apple Silicon)
```

### 签名 + 公证 (Gatekeeper 不拦截)

```bash
# 环境变量 (从 Apple Developer 获取)
export APPLE_ID="your@email.com"
export APPLE_ID_PASSWORD="app-specific-password"
export APPLE_TEAM_ID="YOUR_TEAM_ID"

# electron-builder 自动签 — 在 electron-builder.yml 加:
# mac:
# hardenedRuntime: true
# gatekeeperAssess: false
# entitlements: build/entitlements.mac.plist
# entitlementsInherit: build/entitlements.mac.plist
# notarize:
# teamId: ${APPLE_TEAM_ID}
```

### 上架渠道

| 渠道 | 操作 |
|------|------|
| **GitHub Releases** | 拖入 `.dmg` |
| **官网** | 托管 `.dmg` 直链 |
| **Mac App Store** | `.dmg` → 打包 `.pkg` → App Store Connect → TestFlight → 提交审核 |

### 兼容性

- macOS 12 Monterey ~ macOS 15 Sequoia
- Intel x64 + Apple Silicon arm64 双架构

---

## 三、iOS App Store

### 前置

- macOS + Xcode 16+
- Apple Developer 账号 ($99/年)
- Test-Agent 后端服务器 (公网可达)

### 编译 + 提交

```bash
# 1. 安装 Capacitor
cd mobile && npm install

# 2. 编译前端
cd ../runtime/web && npm run build

# 3. 添加 iOS 平台
cd ../../mobile
npx cap add ios

# 4. 打开 Xcode
npx cap open ios
```

### Xcode 内操作

1. 选 `Product > Archive`
2. Organizer → `Distribute App`
3. 选 `App Store Connect` → Upload
4. 开 [App Store Connect](https://appstoreconnect.apple.com) → 填元数据
5. 提交审核 (通常 1-3 天)

### 必需元数据

- 应用名称: Test-Agent
- 描述: AI Testing Framework — autonomous testing
- 截图: 6.7" + 6.5" + 5.5" (3 套尺寸)
- 隐私标签: 不收集用户数据
- 分类: Developer Tools / Utilities
- 年龄: 17+ (含渗透测试工具)

### 更新

```bash
npx cap sync ios # 前端改了这里同步
npx cap open ios # Xcode Archive 再提交
```

### 兼容性

- iOS 14.0+
- iPhone / iPad 均支持
- PWA 模式无需上架, Safari "添加到主屏幕" 即可

---

## 四、Android Google Play

### 前置

- Android Studio
- Google Play Console 账号 ($25 一次性)
- Java JDK 17+

### 编译 + 提交

```bash
# 1. 安装 Capacitor
cd mobile && npm install

# 2. 编译前端
cd ../runtime/web && npm run build

# 3. 添加 Android 平台
cd ../../mobile
npx cap add android

# 4. 打开 Android Studio
npx cap open android
```

### Android Studio 内操作

1. `Build > Generate Signed Bundle / APK`
2. 选 `Android App Bundle (.aab)` (Play Store 要求)
3. 创建或选择 keystore (保管好!)
4. 生成 `.aab`
5. 开 [Google Play Console](https://play.google.com/console) → 创建应用
6. 上传 `.aab` → 填元数据 → 提交审核 (通常 2-7 天)

### 必需元数据

- 应用名称: Test-Agent
- 简短描述: AI-powered autonomous testing framework
- 完整描述: (见 README.zh-CN.md)
- 截图: 手机 + 平板 + 横屏
- 分类: Tools / Productivity
- 内容分级: 填写问卷获取
- 隐私政策 URL: 需要托管

### 更新

```bash
npx cap sync android # 同步前端改动
npx cap open android # Android Studio Build → upload .aab
```

### 兼容性

- Android 8.0 (API 26)+
- Google Play 商店下载
- 也可直接分发 `.apk` 文件

---

## 五、PWA (无需商店, 即开即用)

### 首次部署

```bash
# 编译前端 (含 manifest + service worker)
cd runtime/web && npm install && npm run build

# 托管 dist/ 到任意静态服务器
# 例: nginx, Vercel, Netlify, GitHub Pages
```

### 用户端

1. 手机浏览器打开部署地址
2. iOS Safari: 点分享 → "添加到主屏幕"
3. Android Chrome: 点菜单 → "安装应用"

### 验证 PWA 配置

Chrome DevTools → Application → Manifest → 检查图标/名称/主题色

### 更新 PWA

重新 `npm run build` → 部署新 `dist/` → service worker 自动更新缓存

### 优势

- 无需商店审核，即时发布
- 跨平台 (iOS/Android/Desktop 全支持)
- 离线可用 (service worker 缓存)
- 用户无需下载安装

---

## 六、CI 自动发布 (全平台)

推送 tag 自动编译所有平台:

```bash
git tag v1.0.0 && git push origin v1.0.0
```

GitHub Actions 自动:
- Windows: PyInstaller + electron-builder → .exe → GitHub Release
- macOS: PyInstaller + electron-builder → .dmg × 2 → GitHub Release
- 未自动编译: iOS/Android (需 macOS + Xcode/Android Studio 手动)

工作流: `.github/workflows/desktop-release.yml`

---

## 七、版本号管理

| 文件 | 更新 |
|------|------|
| `VERSION` | `1.0.0` |
| `runtime/__init__.py` | reads from VERSION |
| `runtime/pyproject.toml` | `version = "1.0.0"` |
| `desktop/package.json` | `"version": "1.0.0"` |
| `desktop/electron/preload.ts` | `"1.0.0"` |
| `mobile/package.json` | `"version": "1.0.0"` |
| `mobile/capacitor.config.json` | `"version": "1.0.0"` |
| `runtime/web/src/App.tsx` | 版本号显示 |

发布前确保以上文件版本一致。

---

## 八、检查清单

发布前逐项核对:

- [ ] `pytest` 128 passed
- [ ] `tagent demo -y` 跑通
- [ ] 版本号 7 文件统一
- [ ] CHANGELOG.md 有新版本条目
- [ ] git tag 已推送
- [ ] CI build 全绿
- [ ] macOS DMG 本地验证能打开
- [ ] Windows .exe 干净机器安装测试
