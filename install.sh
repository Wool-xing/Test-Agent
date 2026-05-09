#!/bin/bash
# Test-Agent 工作流一键部署脚本
# 用法（远程一行）：
#   curl -fsSL https://raw.githubusercontent.com/Wool-xing/Test-Agent/main/install.sh | bash -s -- /path/to/your-test-project
# 用法（本地）：
#   bash install.sh /path/to/your-test-project
set -euo pipefail

# ===== 参数 =====
PROJECT_ROOT="${1:-$(pwd)/test-project}"
REPO_URL="${TEST_AGENT_REPO_URL:-https://github.com/Wool-xing/Test-Agent.git}"
REPO_BRANCH="${TEST_AGENT_REPO_BRANCH:-main}"

echo "=========================================="
echo " Test-Agent 工作流一键部署 V1.0.0"
echo " 仓库:     $REPO_URL ($REPO_BRANCH)"
echo " 项目目录: $PROJECT_ROOT"
echo "=========================================="

# ===== 1. 检查工具 =====
need() { command -v "$1" >/dev/null 2>&1 || { echo "❌ 缺少 $1"; exit 1; }; }
need git
need python3
need node
need npm

# ===== 2. 克隆模板到临时目录 =====
TEMPLATE_DIR="$(mktemp -d)/Test-Agent工作流搭建"
trap 'rm -rf "$(dirname "$TEMPLATE_DIR")"' EXIT

echo "→ 克隆模板..."
git clone --depth 1 --branch "$REPO_BRANCH" "$REPO_URL" "$TEMPLATE_DIR"

# ===== 3. 安装 Claude Code =====
if ! command -v claude >/dev/null 2>&1; then
    echo "→ 安装 Claude Code..."
    npm install -g @anthropic-ai/claude-code
fi

# ===== 4. 创建项目目录结构 =====
echo "→ 创建目录..."
mkdir -p "$PROJECT_ROOT"/.claude/{agents,skills}
mkdir -p "$PROJECT_ROOT"/.github/workflows
mkdir -p "$PROJECT_ROOT"/utils
mkdir -p "$PROJECT_ROOT"/src
mkdir -p "$PROJECT_ROOT"/workspace/{测试计划,需求分析,测试用例,测试数据}
mkdir -p "$PROJECT_ROOT"/workspace/自动化脚本/python/{pages,api,tests,scripts}
mkdir -p "$PROJECT_ROOT"/workspace/自动化脚本/jmeter
mkdir -p "$PROJECT_ROOT"/workspace/执行日志/{allure-results,jmeter-results,jmeter-report,coverage-report,baselines,history,截图,报告}

# ===== 5. 拷贝 Agent / Skill 定义 =====
echo "→ 拷贝 Agent 定义（14 个）..."
for f in 01-测试主管 02-需求分析 03-用例设计 04-环境管理 05-数据准备 06-自动化脚本 07-测试执行 08-Bug管理 09-报告生成 10-移动测试 11-桌面测试 12-视觉游戏测试 13-系统集成测试 14-AI模型测试; do
    cp "$TEMPLATE_DIR/02-专家定义/${f}.md" "$PROJECT_ROOT/.claude/agents/"
done

echo "→ 拷贝 Skill 定义（13 个）..."
for f in smoke-test test-coordinator regression-test testcase-design python-script-gen jmeter-script-gen data-preparation zentao-bug-submission mobile-test desktop-test visual-test system-test ai-test; do
    cp "$TEMPLATE_DIR/03-技能定义/${f}.md" "$PROJECT_ROOT/.claude/skills/"
done

# ===== 6. 配置文件 =====
echo "→ 拷贝配置文件..."
cp "$TEMPLATE_DIR/04-配置文件/conftest.py"      "$PROJECT_ROOT/"
cp "$TEMPLATE_DIR/04-配置文件/pytest.ini"       "$PROJECT_ROOT/"
cp "$TEMPLATE_DIR/04-配置文件/.mcp.json"        "$PROJECT_ROOT/"
cp "$TEMPLATE_DIR/04-配置文件/requirements.txt" "$PROJECT_ROOT/"
[[ -f "$PROJECT_ROOT/.env" ]] || cp "$TEMPLATE_DIR/04-配置文件/.env.example" "$PROJECT_ROOT/.env"

# ===== 7. utils（12 个 .py + __init__）=====
echo "→ 拷贝 utils（24 个）..."
for f in __init__.py api_retry_util.py data_factory.py data_masking.py \
         excel_generator.py flaky_detector.py generate_report.py \
         jmeter_csv_exporter.py jmeter_result_parser.py \
         regression_scope.py zentao_bug_manager.py ci_quality_gate.py \
         mobile_driver.py miniprogram_runner.py desktop_driver.py \
         visual_helper.py iot_helper.py media_validator.py \
         tracing_validator.py mq_helper.py ai_validator.py \
         prd_loader.py websocket_helper.py protocol_helper.py; do
    cp "$TEMPLATE_DIR/05-代码示例/${f}" "$PROJECT_ROOT/utils/"
done

# ===== 8. CI/CD =====
echo "→ 拷贝 CI/CD..."
cp "$TEMPLATE_DIR/06-CICD集成/github-actions-test.yml" "$PROJECT_ROOT/.github/workflows/test.yml"
cp "$TEMPLATE_DIR/06-CICD集成/jenkins-pipeline.groovy" "$PROJECT_ROOT/Jenkinsfile"

# ===== 9. Python 虚拟环境 + 依赖 =====
cd "$PROJECT_ROOT"
if [[ ! -d ".venv" ]]; then
    echo "→ 创建虚拟环境..."
    python3 -m venv .venv
fi
# shellcheck disable=SC1091
source .venv/bin/activate

echo "→ 安装 Python 依赖..."
pip install -r requirements.txt -q
playwright install chromium --with-deps 2>/dev/null || echo "⚠️ Playwright deps 安装失败，UI 测试需手动 'playwright install chromium --with-deps'"

# ===== 10. 完成提示 =====
cat <<EOF

==========================================
 ✅ 部署完成

 项目目录: $PROJECT_ROOT

 下一步：
 1. 编辑 $PROJECT_ROOT/.env（最少 8 必填字段，详见 配置清单.md）
 2. 安装 Java JRE 17 + JMeter 5.6.3 + Allure CLI（详见 部署说明.md）
 3. claude /login                           # 首次登录 Claude Code
 4. cd $PROJECT_ROOT && claude              # 启动
 5. 在 Claude 提示符内: > /smoke-test       # 第一次冒烟验证

==========================================
EOF
