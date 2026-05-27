#!/bin/bash
# Test-Agent 工作流一键部署脚本
#
# 安全提示：curl | bash 存在供应链风险。生产环境建议先 clone 仓库再本地执行：
#   git clone --depth 1 --branch v1.42.0 https://github.com/Wool-xing/Test-Agent.git
#   cd Test-Agent && bash install.sh /path/to/your-test-project
#
# 用法（远程一行，方便快速试用）：
#   curl -fsSL https://raw.githubusercontent.com/Wool-xing/Test-Agent/main/install.sh | bash -s -- /path/to/your-test-project
# 用法（本地）：
#   bash install.sh /path/to/your-test-project
set -euo pipefail

# ===== 参数 =====
PROJECT_ROOT="${1:-$(pwd)/test-project}"
REPO_URL="${TEST_AGENT_REPO_URL:-https://github.com/Wool-xing/Test-Agent.git}"
REPO_BRANCH="${TEST_AGENT_REPO_BRANCH:-main}"

echo "=========================================="
echo " Test-Agent 工作流一键部署 V1.42.0"
echo " 仓库:     $REPO_URL ($REPO_BRANCH)"
echo " 项目目录: $PROJECT_ROOT"
echo "=========================================="

# ===== Idempotency：保留用户敏感数据 =====
PRESERVE_FILES=(".env" "workspace/测试数据/test_data.json"
                "workspace/执行日志/baselines/perf_baseline.json"
                "workspace/regression_modules.yaml")
BACKUP_DIR=""
if [[ -d "$PROJECT_ROOT" ]]; then
    BACKUP_DIR="$(mktemp -d "${TMPDIR:-/tmp}/test-agent-backup-XXXXXXXX")"
    echo "→ 检测到已有项目，备份用户数据到 $BACKUP_DIR"
    for f in "${PRESERVE_FILES[@]}"; do
        if [[ -f "$PROJECT_ROOT/$f" ]]; then
            mkdir -p "$BACKUP_DIR/$(dirname "$f")"
            cp "$PROJECT_ROOT/$f" "$BACKUP_DIR/$f"
            echo "  备份: $f"
        fi
    done
fi

# 完成时恢复用户数据
restore_user_data() {
    if [[ -n "$BACKUP_DIR" ]] && [[ -d "$BACKUP_DIR" ]]; then
        echo "→ 恢复用户数据..."
        for f in "${PRESERVE_FILES[@]}"; do
            if [[ -f "$BACKUP_DIR/$f" ]]; then
                cp "$BACKUP_DIR/$f" "$PROJECT_ROOT/$f"
                echo "  恢复: $f"
            fi
        done
        rm -rf "$BACKUP_DIR"
    fi
}
trap 'restore_user_data; [[ -n "${TEMPLATE_DIR:-}" ]] && rm -rf "$(dirname "$TEMPLATE_DIR")" 2>/dev/null' EXIT

# ===== 1. 检查工具 =====
need() { command -v "$1" >/dev/null 2>&1 || { echo "❌ 缺少 $1"; exit 1; }; }
need git
need node
need npm

# Python 3 检测：Windows 上 python3 可能是 MS Store stub（exit 49 不输出版本），逐个测真可用
PYTHON_BIN=""
for cand in python3 python py; do
    if command -v "$cand" >/dev/null 2>&1; then
        ver_out="$("$cand" --version 2>&1 || true)"
        if [[ "$ver_out" == Python\ 3* ]]; then
            PYTHON_BIN="$cand"
            break
        fi
    fi
done
if [[ -z "$PYTHON_BIN" ]]; then
    echo "❌ 缺少 Python 3（python3 / python / py 均不可用）"
    exit 1
fi
echo "→ 使用 Python: $PYTHON_BIN ($("$PYTHON_BIN" --version 2>&1))"

# ===== 2. 克隆模板到临时目录 =====
TEMPLATE_DIR="$(mktemp -d)/Test-Agent工作流搭建"
# （restore_user_data trap 已在前置 idempotency 段统一处理）

# CI dev mode: 设 TEST_AGENT_LOCAL_SRC=<path> 用本地源代码,跳过 git clone
# (用于 GitHub Actions macos-real-install / linux-real-install job 验当前 PR 改动,
# 而非 fetch default branch)。Production 用户不设此 env, 走 git clone 路径。
if [[ -n "${TEST_AGENT_LOCAL_SRC:-}" ]]; then
    echo "→ [dev mode] 复制本地源代码: $TEST_AGENT_LOCAL_SRC → $TEMPLATE_DIR"
    cp -R "$TEST_AGENT_LOCAL_SRC" "$TEMPLATE_DIR"
else
    echo "→ 克隆模板..."
    git clone --depth 1 --branch "$REPO_BRANCH" "$REPO_URL" "$TEMPLATE_DIR"
fi

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
mkdir -p "$PROJECT_ROOT"/workspace/{测试计划,需求分析,测试用例,测试数据,测试报告}
mkdir -p "$PROJECT_ROOT"/workspace/测试用例/charters
mkdir -p "$PROJECT_ROOT"/workspace/自动化脚本/python/{pages,api,tests,scripts}
mkdir -p "$PROJECT_ROOT"/workspace/自动化脚本/jmeter
mkdir -p "$PROJECT_ROOT"/workspace/执行日志/{allure-results,jmeter-results,jmeter-report,coverage-report,baselines,history,截图}

# ===== 5. 拷贝 Agent / Skill 定义 =====
echo "→ 拷贝 Agent 定义..."
# Glob 全部 [0-9]*.md (业务 agent),自动覆盖未来新增
find "$TEMPLATE_DIR/agents" -maxdepth 1 -name '[0-9]*.md' -exec cp {} "$PROJECT_ROOT/.claude/agents/" \;
agent_count=$(ls "$PROJECT_ROOT/.claude/agents/"[0-9]*.md 2>/dev/null | wc -l)
echo "  已部署 $agent_count 个 Agent"

echo "→ 拷贝 Skill 定义..."
# Glob 顶层业务 skill (排除 README)
find "$TEMPLATE_DIR/skills" -maxdepth 1 -name '*.md' ! -name 'README.md' -exec cp {} "$PROJECT_ROOT/.claude/skills/" \;
# 上游派生子目录 (darwin / karpathy-guidelines / nuwa)
# 注: 用 "${subdir%/}" 去 trailing / — macOS BSD cp 上 `cp -r darwin-skill/ dest/`
# 会展开内容到 dest/, 而非把 darwin-skill 整目录拷过去 (与 GNU cp 行为不同)。
# Linux GNU cp 上两种语法等价, 但 macOS 必须去 / 才能保证子目录结构。
for subdir in "$TEMPLATE_DIR/skills"/*/; do
    [[ -d "$subdir" ]] && cp -r "${subdir%/}" "$PROJECT_ROOT/.claude/skills/"
done
skill_md_count=$(ls "$PROJECT_ROOT/.claude/skills/"*.md 2>/dev/null | wc -l)
skill_dir_count=$(find "$PROJECT_ROOT/.claude/skills/" -maxdepth 1 -mindepth 1 -type d 2>/dev/null | wc -l)
echo "  已部署 $skill_md_count 个业务 Skill + $skill_dir_count 个元 Skill 子目录"

# ===== 6. 配置文件 =====
echo "→ 拷贝配置文件..."
cp "$TEMPLATE_DIR/config/conftest.py"      "$PROJECT_ROOT/"
cp "$TEMPLATE_DIR/config/pytest.ini"       "$PROJECT_ROOT/"
cp "$TEMPLATE_DIR/config/.mcp.json"        "$PROJECT_ROOT/"
cp "$TEMPLATE_DIR/config/requirements.txt" "$PROJECT_ROOT/"
[[ -f "$PROJECT_ROOT/.env" ]] || cp "$TEMPLATE_DIR/config/.env.example" "$PROJECT_ROOT/.env"

# ===== 7. utils（自动扫描全部 .py 文件）=====
echo "→ 拷贝 utils..."
_count=0
while IFS= read -r -d '' f; do
    rel="${f#$TEMPLATE_DIR/utils/}"
    dest="$PROJECT_ROOT/utils/$rel"
    mkdir -p "$(dirname "$dest")"
    cp "$f" "$dest"
    _count=$((_count + 1))
done < <(find "$TEMPLATE_DIR/utils" -name "*.py" -print0)
echo "  ✓ $_count 个 .py 文件已拷贝"

# ===== 8. CI/CD =====
echo "→ 拷贝 CI/CD..."
cp "$TEMPLATE_DIR/ci/github-actions-test.yml" "$PROJECT_ROOT/.github/workflows/test.yml"
cp "$TEMPLATE_DIR/ci/jenkins-pipeline.groovy" "$PROJECT_ROOT/Jenkinsfile"

# ===== 8.5 顶层法律 / 治理 / 路线图文档 =====
echo "→ 拷贝法律 / 治理 / 路线图文档..."
for f in LICENSE NOTICE.md SECURITY.md CONTRIBUTING.md CODE_OF_CONDUCT.md ROADMAP.md README.md README.zh-CN.md CHANGELOG.md VERSION; do
    [[ -f "$TEMPLATE_DIR/$f" ]] && cp "$TEMPLATE_DIR/$f" "$PROJECT_ROOT/"
done

# ===== 9. Python 虚拟环境 + 依赖 =====
cd "$PROJECT_ROOT"
if [[ ! -d ".venv" ]]; then
    echo "→ 创建虚拟环境..."
    "$PYTHON_BIN" -m venv .venv
fi
# Windows Git Bash venv 路径是 Scripts/activate；Linux/Mac 是 bin/activate
if [[ -f ".venv/Scripts/activate" ]]; then
    # shellcheck disable=SC1091
    source .venv/Scripts/activate
else
    # shellcheck disable=SC1091
    source .venv/bin/activate
fi

# Windows GBK 默认编码读 UTF-8 requirements 会 UnicodeDecodeError；强制 UTF-8 mode
export PYTHONUTF8=1
export PYTHONIOENCODING=utf-8

# ===== W7+ install 加速 (PR #62) =====
# (A) CN 网络自动用清华 PyPI 镜像: 跨境 → 国内, 跨境路径提速
# (E) 文档化预期时长 + verbose pip 输出 (用户首次见进度而非黑屏)
# (B uv 待 upstream 修: 实测 uv + Tsinghua 组合协同有 bug, 未达预期 10x)
if [[ -z "${PIP_INDEX_URL:-}" ]]; then
    is_cn=0
    # 允许显式跳过 CN 镜像: TEST_AGENT_NO_CN_MIRROR=1 ./install.sh ...
    if [[ "${TEST_AGENT_NO_CN_MIRROR:-0}" == "1" ]]; then
        is_cn=0
    else
        case "${LANG:-}" in zh*|*CN*|*GB*) is_cn=1 ;; esac
        [[ "$(date +%z 2>/dev/null)" == "+0800" ]] && is_cn=1
    fi
    if [[ $is_cn -eq 1 ]]; then
        echo "→ 检测到 CN 环境, 用清华 PyPI 镜像加速 (export PIP_INDEX_URL=... 可覆盖)"
        export PIP_INDEX_URL=https://pypi.tuna.tsinghua.edu.cn/simple
        export PIP_TRUSTED_HOST=pypi.tuna.tsinghua.edu.cn
    fi
fi

python -m pip install --upgrade pip -q

# 注: 实测 uv + Tsinghua mirror 组合**未带来** 10x 加速 (uv 与 mirror 协同有 bug).
# 改回 pip + 镜像. uv 待 upstream / 改用 PyPI 原站时再启.
INSTALLER="pip"
echo "→ 用 pip 装 Python 依赖 (首次约 5-15 min, CN 网已自动配清华镜像加速)..."

# W4-5 实测 Windows 修: scikit-image / scikit-learn / opencv-python 等 image 包
# 需 C/C++ compiler (Meson build) → Windows 无 MSVC 时 fail。
# 检测 Windows (MINGW/CYGWIN/MSYS), 装时跳过这些可选 image 包, 留 warning。
case "$(uname -s 2>/dev/null || echo unknown)" in
    MINGW*|CYGWIN*|MSYS*)
        echo "→ 检测到 Windows 环境, 跳过需 C 编译器的可选 image 包 (scikit-image / scikit-learn / opencv-python)"
        echo "  如需视觉测试 (visual-test skill), 装 Visual Studio Build Tools 后手动: pip install scikit-image scikit-learn opencv-python"
        # 临时 requirements 排除可选 image 包
        REQ_TMP="$(mktemp -t tagent-req-XXXXXX.txt)"
        grep -vE '^(scikit-image|scikit-learn|opencv-python|opencv-contrib-python)([= ]|$)' requirements.txt > "$REQ_TMP"
        $INSTALLER install -r "$REQ_TMP"
        rm -f "$REQ_TMP"
        ;;
    *)
        $INSTALLER install -r requirements.txt
        ;;
esac

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
