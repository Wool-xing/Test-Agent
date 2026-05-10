# Web Demo · 最小可跑示例（5 分钟）

> 本目录是 **Test-Agent 工作流的最小可运行 Web 测试示例**。无需部署完整模板，无需配 .env，无需禅道/Allure，**纯 pytest + Playwright 跑通 1 个 P0 冒烟用例**。
>
> 验证目标：让首次接触 Test-Agent 的用户在 5 分钟内看到"Page Object 模式 + pytest fixture 复用 + Playwright 浏览器自动化"完整链路。

---

## 5 分钟跑通

> **⚠️ Python 版本要求**：推荐 **Python 3.11 或 3.12**。
> Python 3.13/3.14 上 `greenlet`（playwright 依赖）尚无预编译 wheel，pip install 会触发本地编译失败。
> Python 3.10 也可（与项目主依赖兼容），但 3.11/3.12 是推荐路径。

```bash
cd examples/web-demo

# 0. 确认 Python 版本（应为 3.11 或 3.12）
python --version
# 期望：Python 3.11.x 或 3.12.x

# 1. 建独立 venv（避免污染系统 Python）
python -m venv .venv
source .venv/Scripts/activate    # Windows Git Bash
# 或 .venv\Scripts\activate.bat     # Windows CMD
# 或 source .venv/bin/activate      # macOS/Linux

# 2. 装依赖
pip install --upgrade pip
pip install -r requirements.txt

# 3. 装 Playwright 浏览器（首次必跑，~150MB chromium 下载）
playwright install chromium --with-deps

# 4. 跑用例
pytest -v
```

**预期输出**：

```text
tests/test_smoke.py::test_homepage_title PASSED
tests/test_smoke.py::test_get_started_link_present PASSED

============== 2 passed in 2-5s ==============
```

跑过即说明：✅ Python 环境 OK ✅ Playwright OK ✅ Page Object 模式跑通 ✅ pytest fixture 链路跑通

---

## 文件结构

```text
examples/web-demo/
├── README.md                   ← 本文件
├── requirements.txt            ← 最小依赖（pytest + playwright）
├── pytest.ini                  ← markers + addopts
├── conftest.py                 ← Playwright browser/page fixture
├── pages/
│   ├── __init__.py
│   └── playwright_page.py      ← Page Object 示例
└── tests/
    ├── __init__.py
    └── test_smoke.py           ← 1 个 P0 冒烟用例
```

---

## 与完整 Test-Agent 工作流的关系

| 完整工作流 | 本 demo |
|-----------|---------|
| 14 Agent + 13 Skill + 49 utils | 仅 pytest + playwright |
| `.env` 配置 8 必填 | 不需 `.env` |
| Allure / JMeter / 禅道集成 | 不集成 |
| 冒烟 + 回归 + 性能门禁 | 仅 1 冒烟用例 |
| `install.sh` 一键部署 | `pip install -r requirements.txt` 即可 |

**升级到完整工作流**：见根目录 [`README.md`](../../README.md) Quick Start 段。

---

## 演示对象

本 demo 测试 **`https://playwright.dev`** 官方网站（公开稳定，开发者熟悉）：
- 测试 1：首页标题包含 "Playwright"
- 测试 2：首页存在 "Get started" 链接（hero CTA，稳定多年）

---

## 自定义为你的项目

复制本目录到你的测试项目：

```bash
cp -r examples/web-demo /path/to/your-test-project/tests
```

然后修改：
1. `pages/playwright_page.py` → 改成你的页面对象
2. `tests/test_smoke.py` → 改成你的核心路径用例
3. `pytest.ini` markers → 加你需要的标记（`@p0` / `@smoke` / `@login` 等）

---

## 故障排查

| 现象 | 可能原因 | 解决 |
|------|---------|------|
| `failed-wheel-build-for-install` / `greenlet` 编译失败 | Python 3.13/3.14 缺 wheel | 用 Python 3.11/3.12 重建 venv（见上方"5 分钟跑通"段） |
| `playwright._impl._errors.Error: Executable doesn't exist` | 未装浏览器 | `playwright install chromium --with-deps` |
| `AssertionError: Get started 链接缺失` | playwright.dev 网站改版 | 改 `pages/playwright_page.py::GET_STARTED_LINK` selector |
| `ConnectionError` / 网络超时 | 国内网络访问 playwright.dev 慢 | 改 `tests/test_smoke.py` 的 URL 为本地或国内站点 |
| Windows 中文路径 `UnicodeDecodeError` | 编码问题 | `set PYTHONUTF8=1` 后再跑 |
| `pytest` 没用例 | testpaths 未生效 | 确认在 `examples/web-demo/` 目录下跑 |

---

## License

本 demo 与主项目同 MIT License。详见根目录 [`LICENSE`](../../LICENSE)。
