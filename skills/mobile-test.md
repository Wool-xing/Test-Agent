---
name: mobile-test
description: 移动端测试 Skill。Android / iOS 原生 APP + 微信/支付宝/抖音 小程序。支持真机、模拟器、云真机平台。底层调用 utils/mobile_driver 与 utils/miniprogram_runner。
tools: Read, Write, Bash, Grep, Glob
SKILL_IMPL_STATUS: production
---

# 移动端测试 Skill

## 触发方式

```text
/mobile-test [APP/小程序描述 或 已有 .apk/.ipa 路径]
```

## 🔔 开测前准备清单（必看）

```text
Android：
□ APK 路径 → .env ANDROID_APP_PATH
□ 包名 + 启动 Activity → ANDROID_PACKAGE / ANDROID_ACTIVITY
□ adb devices 列出目标设备 → ANDROID_DEVICE
□ Appium server 启动（curl http://localhost:4723/status）
□ pip 装 Appium-Python-Client + selenium

iOS（必须 macOS 主机）：
□ Xcode + iOS Simulator
□ IPA 路径 + Bundle ID → IOS_APP_PATH / IOS_BUNDLE_ID
□ 真机 UDID 或 模拟器名 → IOS_DEVICE_UDID / IOS_DEVICE_NAME
□ libimobiledevice / xcrun

微信小程序：
□ 微信开发者工具 + CLI 路径 → .env WX_DEVTOOL_CLI
□ 项目源码路径 → WX_PROJECT_PATH
□ AppID → WX_APP_ID
□ pip 装 websocket-client
```

缺项告诉 test-lead，会路由 env-manager 协助配置。

## 适用场景

- Android APK 功能测试
- iOS IPA 功能测试
- 微信 / 支付宝 / 抖音 / 百度 小程序
- 混合应用（原生 + H5 webview）
- 移动专属：弱网 / 后台 / 横竖屏 / 权限弹窗

## 执行流程

### Step 1：设备就绪检查

```bash
# Android
adb devices                              # 列出已连接设备
adb shell getprop ro.product.model       # 设备型号

# iOS
xcrun simctl list booted                 # 已启动模拟器
idevice_id -l                            # 真机 UDID

# Appium server
curl http://localhost:4723/status        # Appium 健康检查
```

### Step 2：启动 Appium server（如未启动）

```bash
# 后台启动
appium --port 4723 &
# 或 docker-compose up -d appium
```

### Step 3：构建 desired_capabilities

由 `mobile-tester` agent 生成。优先级：用户传参 > .env > 默认值。

### Step 4：执行测试

```bash
# Android P0 冒烟
pytest -m "mobile and android and p0" -v --timeout=120

# iOS 完整
pytest -m "mobile and ios" -n 1 --reruns=2

# 小程序
pytest -m "miniprogram and wx" -v
```

### Step 5：性能采集（可选）

```bash
python -m utils.mobile_driver collect-perf \
    --platform android \
    --package com.example.app \
    --duration 60 \
    --output workspace/测试报告/{项目名}/mobile-perf/
```

### Step 5b：Android Monkey 稳定性（可选，长时压测）

```bash
# 1 万事件随机压测
python -m utils.mobile_driver monkey \
    --package com.example.app \
    --events 10000 \
    --throttle 200 \
    --seed 42

# 退出码 0 = 稳定（无 crash 无 ANR），非 0 = 失败
```

或 pytest 集成：

```bash
pytest -m "mobile and android and stability" -v
```

monkey 自动产出：
- `workspace/测试报告/{项目名}/monkey/monkey_<package>_<时间>.log`（事件序列）
- `workspace/测试报告/{项目名}/monkey/monkey_<package>_<时间>.json`（摘要：crash/anr/duration）
- `workspace/测试报告/{项目名}/logcat/logcat_<时间>.log`（同步归档）

### Step 6：报告与归档

- Allure（功能）
- 移动 perf JSON（性能）
- logcat / syslog 归档
- 截图 / 录屏

## 质量门禁

| 指标 | 要求 |
|------|------|
| P0 用例通过率 | ≥95%（与全栈 smoke 门禁一致） |
| Crash 率 | < 0.1% |
| ANR 率（Android） | < 0.05% |
| 启动时间（冷启动） | < 3s |
| FPS（关键页面） | ≥ 55 |
| 内存峰值 | 业务约定（如 < 300MB） |
| **Monkey 稳定性（1 万事件）** | **crash=0 / anr=0** |

## 跨平台并行

```bash
# 同时跑 Android + iOS（不同端各自 worker）
pytest -m "mobile and p0" -n 2 --dist=loadgroup
```

## 云真机集成（可选）

`.env` 配置 `SAUCELABS_*` 或 `BROWSERSTACK_*`，agent 自动切换 hub URL。

```python
# utils/mobile_driver.py 自动读取
from utils.mobile_driver import get_driver

driver = get_driver(
    platform="android",
    use_cloud=True,    # 若 .env 配置了云真机凭证则自动用云
)
```

## 弱网 / 后台 / 横竖屏

```python
# 弱网（Android adb）
driver.execute_script('mobile: shell', {
    "command": "tc qdisc add dev wlan0 root tbf rate 100kbit burst 32kbit latency 400ms",
})

# 后台 5 秒
driver.background_app(5)

# 横屏
driver.orientation = "LANDSCAPE"
```

## 输出文件

```text
workspace/
├── 自动化脚本/python/mobile/             # 移动端 page object + 用例
├── 自动化脚本/python/miniprogram/        # 小程序用例
└── 测试报告/
    ├── mobile-perf/                     # 性能采集 JSON
    ├── logcat/                          # Android 日志
    ├── ios-syslog/                      # iOS 日志
    └── 截图/mobile_*.png
```
