---
id: desktop-testing-windows
category: 07-platforms
level: 中级
name_zh: Windows 桌面应用测试(EXE / Win32 / UI Automation)
name_en: Windows Desktop App Testing (EXE / Win32 / UI Automation)
one_liner_zh: pywinauto+UIA 是 .exe 自动化首选,PyAutoGUI 像素级仅兜底
one_liner_en: pywinauto+UIA is first pick for .exe automation; PyAutoGUI pixel-level only as fallback
authority:

  - "Microsoft UI Automation API https://learn.microsoft.com/en-us/dotnet/framework/ui-automation/"
  - "pywinauto Documentation https://pywinauto.readthedocs.io"
  - "ISTQB Advanced Test Automation Engineer §4.3 Platforms"
  - "Microsoft Engineering Fundamentals Desktop Testing Playbook"
confidence: high
last_reviewed: 2026-05-12
reviewer: agent-curator
when_to_use: 被测物 = .exe / .msi Windows 桌面应用 / WPF / WinForms / Electron(可换 Playwright Electron)
common_pitfall:

  - "用 PyAutoGUI 像素 → 屏幕分辨率变即碎"
  - "不锁定 AutomationId(只用名称) → 多语言版本失效"
  - "未处理 UAC 提权 / 模态对话框"
  - "Electron 应用还用 pywinauto → 应用 Playwright Electron API"
example: |
  ```python
  from pywinauto import Application

  app = Application(backend="uia").start("notepad.exe")
  app.UntitledNotepad.Edit.type_keys("hello", with_spaces=True)
  app.UntitledNotepad.menu_select("File -> Save")
  ```
related_to: [desktop-testing-macos, electron-testing, visual-regression]
reading_zh:

  - "腾讯 TMQ 公众号《Windows 桌面自动化实践》"
reading_en:

  - https://pywinauto.readthedocs.io/en/latest/getting_started.html
  - https://learn.microsoft.com/en-us/dotnet/framework/ui-automation/ui-automation-overview
---

# Windows 桌面应用测试

## 三层模型(必懂)

| 层 | 工具 | 稳定性 | 何时用 |
| ---- | ------ | -------- | -------- |
|**API 层**| 直接调 DLL / COM / IPC | 最稳 | 业务逻辑测试 |
|**UI Automation 层**| pywinauto + UIA / WinAppDriver | 稳定 | 大多数场景默认 |
|**Visual 层**| PyAutoGUI + OpenCV / Airtest OCR | 最脆,易碎 | 无 UIA 树时兜底(游戏/Canvas) |

## Test-Agent 路由逻辑

被测物 PE32 → `desktop-tester` 专家(agents/11-桌面测试.md)→ `utils/desktop_driver.py` 调用 pywinauto。

## 为什么 Agent 选 pywinauto 而非 Playwright?

- Playwright**只支持 Web/Electron**,不能直接驱动 Win32 进程
- pywinauto 基于微软标准 UIA(IAccessible2),与系统辅助技术兼容
- Visual 层用 Airtest 仅作"找不到 UIA 元素时"兜底
