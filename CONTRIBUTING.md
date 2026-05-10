# 贡献指南

欢迎扩展本项目。所有新增 agent / skill / utils 流程统一在此文档。

---

## 添加新 Agent

1. 选定分类（核心通用 9 / 平台扩展 5）
2. 文件命名 `15-XXX.md`（按编号递增）
3. 顶部 YAML frontmatter（必含 `name` / `description` / `tools`）
4. 编写：职责 / 工具栈 / Page Object 或调用模板 / 协作输出
5. **同步**：
   - `02-专家定义/README.md` 加一行
   - `00-项目导航.md` 加一行
   - `01-测试主管.md` 路由表（如平台扩展）
   - `utils/prd_loader.PLATFORM_KEYWORDS` 加关键词（如平台扩展）
   - `install.sh` agents 数组加文件名
   - `01-快速开始/部署说明.md` PowerShell + bash 拷贝清单加

---

## 添加新 Skill

1. 选定分类（通用 8 / 平台专项 5）
2. 文件命名 `<verb>-<noun>.md`（如 `chaos-test.md`）
3. 顶部 YAML frontmatter
4. 必含章节：
   - 🔔 开测前准备清单（平台 skill 必有）
   - 触发方式
   - 适用场景
   - 执行流程
   - 质量门禁
   - 输出文件
5. **同步**：
   - `03-技能定义/README.md` 加一行
   - `00-项目导航.md` 加一行
   - `01-快速开始/使用手册.md` skill 详解段加描述
   - `01-测试主管.md` 快速命令清单加一行
   - `install.sh` skills 数组加文件名
   - `01-快速开始/部署说明.md` 拷贝清单加

---

## 添加新 utils

1. 选定分类（核心 / 平台 / 协议 / 非功能 / 用例方法 / 测试类型 / 安全增强 / DB-契约-API / 移动专项 / a11y-i18n / 度量 / 区块链-AI 对抗 / 报告-SLO-邮件-减重 / 输入加载）
2. 文件名小写下划线（如 `chaos_helper.py`）
3. 顶部 docstring 标注被引用方
4. 必含：公开 API + CLI（argparse）
5. **同步**：
   - `05-代码示例/README.md` 表格加一行
   - `00-项目导航.md` 对应分类加一行
   - `04-配置文件/requirements.txt` 加新依赖（标 [稳定层]/[可选]/[外部]）
   - `04-配置文件/.env.example` 加配置字段
   - `04-配置文件/conftest.py` `pytest_configure` 加产出目录
   - `04-配置文件/pytest.ini` markers 加新标记
   - `install.sh` utils 数组 + 数字
   - `01-快速开始/部署说明.md` 拷贝清单 + 数字

---

## 添加新 marker

`pytest.ini` markers 段加一行，**必须**：
- 全小写下划线
- 注释说明用途
- 同步到 `00-项目导航.md` 维度表（如适用）

---

## 添加新 .env 字段

1. `04-配置文件/.env.example` 加（带注释）
2. `01-快速开始/配置清单.md` 字段说明加一行
3. `04-配置文件/conftest.py` `EnvConfig` 加字段（如功能必需）
4. CI yml / Jenkins Credentials 同步（如 CI 需要）

---

## 提交规范（Conventional Commits）

```
feat(agent): 加 15-AR测试 专家
fix(utils): jmeter_result_parser 修复 timeStamp 排序
docs(readme): 更新覆盖矩阵
chore(deps): 升级 pytest 7.4.3 → 7.5.0
ci(actions): pip-audit 加 --strict
refactor(skill): smoke-test 改并行 step
test(utils): data_factory 加 cleanup 单测
perf(jmeter): 减少不必要心跳
```

---

## PR 流程

1. Fork → 新建 feature 分支（`feat/xxx` / `fix/xxx`）
2. 改动 + 同步上述清单
3. 本地跑：
   ```bash
   pytest --collect-only       # 无 ImportError
   ruff check workspace/ utils/
   pip-audit -r requirements.txt --strict
   ```
4. 提 PR → 等 Dependabot / CI 绿灯 → reviewer 审 → merge

---

## 自检脚本（一键验证项目完整性）

```bash
ls 02-专家定义/[0-9]*.md | wc -l   # 14（或 +N）
ls 03-技能定义/*.md | grep -v README | wc -l  # 13（或 +N）
ls 05-代码示例/*.py | wc -l         # 49（或 +N）
grep -c "^    [a-z_]+:" 04-配置文件/pytest.ini  # markers 数
python -c "from utils.api_retry_util import call_with_retry; print('OK')"
pytest --collect-only
```
