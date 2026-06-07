---
name: visual-test
description: 视觉/游戏测试 Skill。基于图像识别（Airtest）+ OCR + SSIM 对比。适合游戏、Canvas/WebGL、富图形界面。底层调用 utils/visual_helper。
tools: Read, Write, Bash, Grep, Glob
SKILL_IMPL_STATUS: production
---

# 视觉/游戏测试 Skill

## 触发方式

```text
/visual-test [应用描述 或 Airtest 项目路径]
```

## 🔔 开测前准备清单（必看）

```text
□ Airtest 已装（pip install airtest）
□ 模板图（关键 UI 元素截图）→ workspace/自动化脚本/python/visual/images/
□ 设备 URI → AIRTEST_DEVICE_URI
   - Android: Android://127.0.0.1:5037/<serial>
   - Windows: Windows:///?title_re=<窗口标题正则>
   - Web: 需先启 chromium remote-debugging
□ OCR 引擎（如需文字识别）：tesseract 已装 → TESSERACT_CMD
□ 视觉回归基线 → workspace/自动化脚本/python/visual/baselines/
```

## 适用场景

- 手游 / PC 游戏 / 网页游戏
- Canvas / WebGL 应用（地图、图表、画板）
- 视频编辑 / 设计软件 / 3D 工具
- 视觉回归（防意外 UI 变更）

## 执行流程

### Step 1：环境检查

```bash
python -c "import airtest; print(airtest.__version__)"
python -c "import pytesseract; print(pytesseract.get_tesseract_version())"
python -c "import cv2; print(cv2.__version__)"
```

### Step 2：模板图准备

将关键 UI 元素截图作为模板，放入 `workspace/自动化脚本/python/visual/images/`，命名规范：
- `login_btn.png`、`settings_icon.png` 等语义化命名
- 多分辨率：`login_btn_1080p.png`、`login_btn_720p.png`

### Step 3：执行测试

```bash
# 视觉冒烟（Airtest）
pytest -m "visual and p0" -v

# 视觉回归（与 baseline 对比）
pytest -m "visual and regression" -v

# 仅 OCR 验证
pytest -m "visual and ocr" -v
```

### Step 4：视觉差异 diff

测试失败时自动生成 diff 高亮图：

```bash
python -m utils.visual_helper diff \
    --current workspace/测试报告/{项目名}/screenshots/login_current.png \
    --baseline workspace/自动化脚本/python/visual/baselines/login_baseline.png \
    --output workspace/测试报告/{项目名}/screenshots/visual-diff/login_diff.png
```

### Step 5：基线更新（如确认 UI 变更合理）

```bash
cp workspace/测试报告/{项目名}/screenshots/login_current.png \
   workspace/自动化脚本/python/visual/baselines/login_baseline.png
git add workspace/自动化脚本/python/visual/baselines/
git commit -m "chore: update visual baseline for login"
```

## 质量门禁

| 指标 | 要求 |
|------|------|
| P0 视觉用例通过率 | ≥95% |
| 视觉相似度（SSIM） | ≥ 0.95 |
| OCR 字符识别准确率 | ≥ 90%（对清晰文字） |
| 模板匹配 threshold | ≥ 0.85 |

## 输出文件

```text
workspace/
├── 自动化脚本/python/visual/
│   ├── images/                          # 模板图
│   ├── baselines/                       # 视觉回归基线
│   └── tests/
└── 测试报告/
    ├── screenshots/visual_*.png
    ├── screenshots/visual-diff/         # diff 高亮图
    └── screenshots/airtest-report/      # Airtest HTML
```
