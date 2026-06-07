#!/usr/bin/env python3
"""Test-Agent 一键部署脚本（跨平台：Windows / macOS / Linux）

前置条件：
    Python 3.x — 脚本运行前提，需手动安装：
        Windows:  winget install Python.Python.3.13
        macOS:    brew install python@3
        Linux:    sudo apt install python3  (或 dnf/yum/pacman)

    Git / Node.js — 脚本自动检测并安装（winget / brew / apt）

用法：
    python install.py /path/to/your-test-project      # 完整安装到指定目录
    python install.py                                  # 完整安装，默认 ./Test-Agent
    python install.py --update                         # 轻量更新当前目录
    python install.py /path/to/project --update        # 轻量更新指定目录

安全提示：不要 pipe-to-python。先下载再审查后执行：
    curl -fsSL -o install.py https://raw.githubusercontent.com/Wool-xing/Test-Agent/main/install.py
    python install.py /path/to/your-test-project

环境变量（可选）：
    TEST_AGENT_REPO_URL      仓库 URL
    TEST_AGENT_REPO_BRANCH   分支名（默认 main）
    TEST_AGENT_LOCAL_SRC     CI 用：本地源码路径，跳过 git clone
    TEST_AGENT_NO_CN_MIRROR  设为 1 跳过清华 PyPI 镜像
"""

import os
import stat
import sys
import shutil
import subprocess
import tempfile
import glob
import platform
import argparse

# Windows 中文终端默认 GBK，Unicode 输出（✓ ✅ → ⚠）直接炸。
# 强制 UTF-8 输出，避免 UnicodeEncodeError。
if sys.stdout.encoding is not None and sys.stdout.encoding.upper() != "UTF-8":
    sys.stdout.reconfigure(encoding="utf-8")


def _parse_args():
    """解析命令行参数。"""
    parser = argparse.ArgumentParser(
        description="Test-Agent 一键部署脚本",
        epilog="安全提示：不要 pipe-to-python。先下载再审查后执行。",
    )
    parser.add_argument(
        "path", nargs="?", default=None,
        help="项目目录路径（默认: ./Test-Agent；--update 模式下默认当前目录）",
    )
    parser.add_argument(
        "--update", action="store_true",
        help="轻量更新：仅同步新文件 + 依赖，保留用户数据和 .venv",
    )
    _args = parser.parse_args()
    return _args


_ARGS = _parse_args()
UPDATE_MODE = _ARGS.update
IS_WINDOWS = platform.system() == "Windows"

# 部署后的目录名（settings.py 默认值针对源码，部署后 .env 覆盖为这些值）
DEPLOY_EXPERTS_DIR = "agents"
DEPLOY_SKILLS_DIR = "skills"

if _ARGS.path:
    PROJECT_ROOT = _ARGS.path
elif UPDATE_MODE:
    PROJECT_ROOT = os.getcwd()
else:
    PROJECT_ROOT = "D:\\Test-Agent" if IS_WINDOWS else os.path.join(os.getcwd(), "Test-Agent")

# 验证目标路径的驱动器是否存在
if IS_WINDOWS and len(PROJECT_ROOT) >= 2 and PROJECT_ROOT[1] == ":":
    drive = PROJECT_ROOT[:3]
    if not os.path.exists(drive):
        print(f"❌ 目标驱动器不存在: {drive}")
        print(f"   请指定有效路径: python install.py <路径>")
        sys.exit(1)
REPO_URL = os.environ.get("TEST_AGENT_REPO_URL", "https://github.com/Wool-xing/Test-Agent.git")
REPO_BRANCH = os.environ.get("TEST_AGENT_REPO_BRANCH", "main")

PRESERVE_FILES = [
    ".env",
    "quality_gates.yaml",
    os.path.join("workspace", "测试数据", "test_data.json"),
    os.path.join("workspace", "测试报告", "baselines", "perf_baseline.json"),
    "workspace/regression_modules.yaml",
]


def banner():
    mode = "轻量更新" if UPDATE_MODE else "一键部署"
    print("=" * 50)
    print(f" Test-Agent {mode}")
    print(f" 仓库:     {REPO_URL} ({REPO_BRANCH})")
    print(f" 项目目录: {PROJECT_ROOT}")
    print("=" * 50)


def ensure_prerequisites():
    """检测并在可能时自动安装 Git / Node.js。Python 需用户手动安装。"""
    missing = []
    if shutil.which("git") is None:
        missing.append("git")
    if shutil.which("node") is None or shutil.which("npm") is None:
        missing.append("node")

    if not missing:
        print("✓ 前置工具就绪: git, node, npm")
        return

    print(f"→ 检测到缺失工具: {', '.join(missing)}")
    installed = _auto_install(missing)

    still = [m for m in missing if m not in installed]
    if still:
        print(f"❌ 以下工具安装失败，请手动安装后重试: {', '.join(still)}")
        _print_manual_hint(still)
        sys.exit(1)

    print("✓ 前置工具就绪")


def _auto_install(missing):
    """尝试通过平台包管理器安装缺失工具。返回成功安装的工具列表。"""
    installed = []
    if IS_WINDOWS:
        installed = _install_winget(missing)
    elif platform.system() == "Darwin":
        installed = _install_brew(missing)
    else:
        installed = _install_linux_pm(missing)
    return installed


def _install_winget(missing):
    """Windows: 用 winget 安装。"""
    if shutil.which("winget") is None:
        print("⚠️ 未检测到 winget，请手动安装")
        return []
    installed = []
    pkgs = {"git": "Git.Git", "node": "OpenJS.NodeJS.LTS"}
    for tool in missing:
        pkg = pkgs.get(tool)
        if pkg is None:
            continue
        print(f"→ winget install {pkg} ...")
        try:
            subprocess.run(
                ["winget", "install", "--silent", "--accept-source-agreements", pkg],
                check=True, timeout=300,
            )
            installed.append(tool)
            print(f"  ✓ {tool} 安装完成")
        except Exception as e:
            print(f"  ⚠️ {tool} 安装失败: {e}")
    return installed


def _install_brew(missing):
    """macOS: 用 Homebrew 安装。"""
    if shutil.which("brew") is None:
        print("⚠️ 未检测到 Homebrew，请手动安装: /bin/bash -c \"$(curl -fsSL https://raw.githubusercontent.com/Homebrew/install/HEAD/install.sh)\"")
        return []
    installed = []
    for tool in missing:
        print(f"→ brew install {tool} ...")
        try:
            subprocess.run(["brew", "install", tool], check=True, timeout=300)
            installed.append(tool)
            print(f"  ✓ {tool} 安装完成")
        except Exception as e:
            print(f"  ⚠️ {tool} 安装失败: {e}")
    return installed


def _install_linux_pm(missing):
    """Linux: 检测包管理器并安装。"""
    pm = None
    for candidate, update_cmd, install_cmd in [
        ("apk",      ["sudo", "apk", "update"],             ["sudo", "apk", "add"]),
        ("apt-get",  ["sudo", "apt-get", "update", "-qq"],  ["sudo", "apt-get", "install", "-y", "-qq"]),
        ("dnf",      None,                                   ["sudo", "dnf", "install", "-y", "-q"]),
        ("yum",      None,                                   ["sudo", "yum", "install", "-y", "-q"]),
        ("pacman",   None,                                   ["sudo", "pacman", "-S", "--noconfirm"]),
        ("zypper",   None,                                   ["sudo", "zypper", "install", "-y"]),
    ]:
        if shutil.which(candidate):
            pm = (candidate, update_cmd, install_cmd)
            break

    if pm is None:
        print("⚠️ 未检测到已知包管理器，请手动安装")
        return []

    pm_name, update_cmd, install_cmd = pm
    pkgs = {"git": ["git"], "node": ["nodejs", "npm"]}

    if update_cmd:
        try:
            subprocess.run(update_cmd, check=True, timeout=120)
        except Exception:
            pass

    installed = []
    for tool in missing:
        pkg_list = pkgs.get(tool, [tool])
        cmd = install_cmd + pkg_list
        print(f"→ {pm_name} install {tool} ...")
        try:
            subprocess.run(cmd, check=True, timeout=300)
            installed.append(tool)
            print(f"  ✓ {tool} 安装完成")
        except Exception as e:
            print(f"  ⚠️ {tool} 安装失败: {e}")
    return installed


def _print_manual_hint(missing):
    """打印手动安装提示。"""
    hints = {
        "git":  "Git:      https://git-scm.com/downloads",
        "node": "Node.js:  https://nodejs.org/  (LTS 版本)",
    }
    print("→ 手动安装指引：")
    for m in missing:
        if m in hints:
            print(f"  {hints[m]}")
    print("→ 安装完成后重新运行: python install.py")


def find_python():
    """跨平台检测 Python 3，排除 MS Store stub。"""
    candidates = ["python3", "python", "py"]
    for cand in candidates:
        path = shutil.which(cand)
        if path is None:
            continue
        if IS_WINDOWS and "WindowsApps" in path:
            # MS Store stub，跳过
            continue
        try:
            out = subprocess.run([cand, "--version"], capture_output=True, text=True).stdout
        except Exception:
            continue
        if out.startswith("Python 3"):
            return cand
    print("❌ 缺少 Python 3（python3 / python / py 均不可用或为 MS Store stub）")
    sys.exit(1)


def backup_user_data(project_root):
    """幂等部署：备份用户敏感数据。"""
    backed = {}
    if not os.path.isdir(project_root):
        return backed
    tmp = tempfile.mkdtemp(prefix="test-agent-backup-")
    print(f"→ 检测到已有项目，备份用户数据到 {tmp}")
    for f in PRESERVE_FILES:
        src = os.path.join(project_root, f)
        if os.path.isfile(src):
            dst = os.path.join(tmp, f)
            os.makedirs(os.path.dirname(dst), exist_ok=True)
            shutil.copy2(src, dst)
            backed[f] = dst
            print(f"  备份: {f}")
    backed["__tmp__"] = tmp
    return backed


def restore_user_data(project_root, backed):
    """恢复用户数据并清理临时目录。"""
    tmp = backed.pop("__tmp__", None)
    if not backed:
        return
    print("→ 恢复用户数据...")
    for f, src in backed.items():
        dst = os.path.join(project_root, f)
        os.makedirs(os.path.dirname(dst), exist_ok=True)
        shutil.copy2(src, dst)
        print(f"  恢复: {f}")
    if tmp and os.path.isdir(tmp):
        shutil.rmtree(tmp)


def create_dirs(project_root):
    """创建项目目录结构。"""
    print("→ 创建目录...")
    dirs = [
        DEPLOY_EXPERTS_DIR,                          # runtime 直读（registry / catalog）
        DEPLOY_SKILLS_DIR,                          # runtime 直读
        os.path.join(".claude", DEPLOY_EXPERTS_DIR), # Claude Code 自动发现
        os.path.join(".claude", DEPLOY_SKILLS_DIR), # Claude Code 自动发现
        os.path.join(".github", "workflows"),
        "utils",
        "src",
        os.path.join("workspace", "测试计划"),
        os.path.join("workspace", "需求分析"),
        os.path.join("workspace", "测试用例"),
        os.path.join("workspace", "测试数据"),
        os.path.join("workspace", "测试报告"),
        os.path.join("workspace", "自动化脚本", "python", "pages"),
        os.path.join("workspace", "自动化脚本", "python", "api"),
        os.path.join("workspace", "自动化脚本", "python", "tests"),
        os.path.join("workspace", "自动化脚本", "python", "scripts"),
        os.path.join("workspace", "自动化脚本", "jmeter"),
        "memory",
    ]
    for d in dirs:
        os.makedirs(os.path.join(project_root, d), exist_ok=True)


def copy_agents(template_dir, project_root):
    """拷贝 Agent 定义到 agents/（runtime 用）和 .claude/agents/（Claude Code 用）。"""
    print("→ 拷贝 Agent 定义...")
    # 兼容新旧仓库结构：新(ai/agents) 优先，旧(agents) 兜底
    agents_dir = os.path.join(template_dir, "ai", "agents")
    if not os.path.isdir(agents_dir):
        agents_dir = os.path.join(template_dir, "agents")
    # runtime 路径
    runtime_dest = os.path.join(project_root, DEPLOY_EXPERTS_DIR)
    os.makedirs(runtime_dest, exist_ok=True)
    # Claude Code 路径
    claude_dest = os.path.join(project_root, ".claude", DEPLOY_EXPERTS_DIR)
    os.makedirs(claude_dest, exist_ok=True)
    count = 0
    for f in glob.glob(os.path.join(agents_dir, "[0-9]*.md")):
        shutil.copy2(f, runtime_dest)
        shutil.copy2(f, claude_dest)
        count += 1
    print(f"  已部署 {count} 个 Agent（agents/ + .claude/agents/）")


def copy_skills(template_dir, project_root):
    """拷贝 Skill 定义到 skills/（runtime 用）和 .claude/skills/（Claude Code 用）。"""
    print("→ 拷贝 Skill 定义...")
    # 兼容新旧仓库结构：新(ai/skills) 优先，旧(skills) 兜底
    skills_dir = os.path.join(template_dir, "ai", "skills")
    if not os.path.isdir(skills_dir):
        skills_dir = os.path.join(template_dir, "skills")
    runtime_dest = os.path.join(project_root, DEPLOY_SKILLS_DIR)
    os.makedirs(runtime_dest, exist_ok=True)
    claude_dest = os.path.join(project_root, ".claude", DEPLOY_SKILLS_DIR)
    os.makedirs(claude_dest, exist_ok=True)

    md_count = 0
    for f in glob.glob(os.path.join(skills_dir, "*.md")):
        if os.path.basename(f) == "README.md":
            continue
        shutil.copy2(f, runtime_dest)
        shutil.copy2(f, claude_dest)
        md_count += 1

    dir_count = 0
    for entry in os.listdir(skills_dir):
        sub = os.path.join(skills_dir, entry)
        if os.path.isdir(sub):
            # runtime
            rdst = os.path.join(runtime_dest, entry)
            if os.path.exists(rdst):
                shutil.rmtree(rdst)
            shutil.copytree(sub, rdst)
            # Claude Code
            cdst = os.path.join(claude_dest, entry)
            if os.path.exists(cdst):
                shutil.rmtree(cdst)
            shutil.copytree(sub, cdst)
            dir_count += 1

    print(f"  已部署 {md_count} 个业务 Skill + {dir_count} 个元 Skill 子目录（skills/ + .claude/skills/）")


def _ensure_env_overrides(env_path: str) -> None:
    """确保 .env 中包含部署后路径覆盖。"""
    overrides = {
        "TAGENT_EXPERTS_DIR": DEPLOY_EXPERTS_DIR,
        "TAGENT_SKILLS_DIR": DEPLOY_SKILLS_DIR,
    }
    if os.path.isfile(env_path):
        with open(env_path, "r", encoding="utf-8") as f:
            content = f.read()
        missing = [k for k, v in overrides.items() if k not in content]
        if missing:
            with open(env_path, "a", encoding="utf-8") as f:
                f.write("\n# 部署后路径覆盖（AI模式/CLI模式共用 agents/ skills/ 非 ai/ 子目录）\n")
                for k in missing:
                    f.write(f"{k}={overrides[k]}\n")


def copy_config(template_dir, project_root):
    """拷贝配置文件。"""
    print("→ 拷贝配置文件...")
    # 兼容新旧仓库结构：新(deploy/config) 优先，旧(config) 兜底
    config_dir = os.path.join(template_dir, "deploy", "config")
    if not os.path.isdir(config_dir):
        config_dir = os.path.join(template_dir, "config")
    files = [
        "conftest.py", "pytest.ini", ".mcp.json", "requirements.txt",
        "check_version.py", "quality_gates.yaml",
    ]
    for f in files:
        src = os.path.join(config_dir, f)
        if os.path.isfile(src):
            shutil.copy2(src, project_root)

    # 拷贝项目模板（STARTUP.md.tpl / .env.tpl / .tagent.yml.tpl / matrix.yaml 等）
    tmpl_src = os.path.join(config_dir, "templates")
    tmpl_dst = os.path.join(project_root, "templates")
    if os.path.isdir(tmpl_src):
        if os.path.exists(tmpl_dst):
            shutil.rmtree(tmpl_dst)
        shutil.copytree(tmpl_src, tmpl_dst)

    # .env — 仅在不存在时创建
    env_dst = os.path.join(project_root, ".env")
    if not os.path.isfile(env_dst):
        env_src = os.path.join(config_dir, ".env.example")
        if os.path.isfile(env_src):
            shutil.copy2(env_src, env_dst)

    # 确保部署后路径覆盖存在（settings.py 默认值针对源码，部署后需覆盖）
    _ensure_env_overrides(env_dst)

    # .claude/settings.json — 部署版本检查 hook，仅在不存在时创建
    claude_dir = os.path.join(project_root, ".claude")
    settings_dst = os.path.join(claude_dir, "settings.json")
    if not os.path.isfile(settings_dst):
        settings_src = os.path.join(config_dir, "settings.json")
        if os.path.isfile(settings_src):
            os.makedirs(claude_dir, exist_ok=True)
            shutil.copy2(settings_src, settings_dst)


def copy_utils(template_dir, project_root):
    """拷贝 utils 目录下所有 .py 文件。"""
    print("→ 拷贝 utils...")
    utils_src = os.path.join(template_dir, "utils")
    utils_dst = os.path.join(project_root, "utils")
    count = 0
    for root, _, files in os.walk(utils_src):
        for f in files:
            if f.endswith(".py"):
                src = os.path.join(root, f)
                rel = os.path.relpath(src, utils_src)
                dst = os.path.join(utils_dst, rel)
                os.makedirs(os.path.dirname(dst), exist_ok=True)
                shutil.copy2(src, dst)
                count += 1
    print(f"  ✓ {count} 个 .py 文件已拷贝")


def copy_runtime(template_dir, project_root):
    """拷贝 runtime 目录（pyproject.toml / Python / 前端 / Docker / MCP / 配置等）。"""
    print("→ 拷贝 runtime...")
    runtime_src = os.path.join(template_dir, "runtime")
    runtime_dst = os.path.join(project_root, "runtime")
    count = 0
    skip_dirs = {"__pycache__", ".ruff_cache", ".pytest_cache", ".egg-info",
                 "node_modules", ".git"}
    skip_ext = {".pyc", ".pyo"}
    skip_files = {".coverage", ".dockerignore", "tsconfig.tsbuildinfo"}
    for root, dirs, files in os.walk(runtime_src):
        dirs[:] = [d for d in dirs if d not in skip_dirs and not d.startswith(".")]
        for f in files:
            _, ext = os.path.splitext(f)
            if ext in skip_ext or f in skip_files:
                continue
            src = os.path.join(root, f)
            rel = os.path.relpath(src, runtime_src)
            dst = os.path.join(runtime_dst, rel)
            os.makedirs(os.path.dirname(dst), exist_ok=True)
            shutil.copy2(src, dst)
            count += 1
    print(f"  ✓ {count} 个文件已拷贝")


def copy_ci(template_dir, project_root):
    """拷贝 CI/CD 文件。"""
    print("→ 拷贝 CI/CD...")
    ci_dir = os.path.join(template_dir, "ci")
    shutil.copy2(
        os.path.join(ci_dir, "github-actions-test.yml"),
        os.path.join(project_root, ".github", "workflows", "test.yml"),
    )
    shutil.copy2(
        os.path.join(ci_dir, "jenkins-pipeline.groovy"),
        os.path.join(project_root, "Jenkinsfile"),
    )


def copy_top_level_docs(template_dir, project_root):
    """拷贝顶层法律 / 治理 / 路线图文档。"""
    print("→ 拷贝法律 / 治理 / 路线图文档...")
    docs = [
        "LICENSE", "NOTICE.md", "SECURITY.md", "CONTRIBUTING.md",
        "CODE_OF_CONDUCT.md", "ROADMAP.md", "README.md", "README.zh-CN.md",
        "CHANGELOG.md", "VERSION", "FULL_GUIDE.md", "AGENTS.md", "CLAUDE.md",
        "tagent.yml.example",
    ]
    for f in docs:
        src = os.path.join(template_dir, f)
        if os.path.isfile(src):
            shutil.copy2(src, project_root)


def setup_venv(python_bin, project_root):
    """创建 Python 虚拟环境并安装依赖。"""
    venv_dir = os.path.join(project_root, ".venv")
    if not os.path.isdir(venv_dir):
        print("→ 创建虚拟环境...")
        subprocess.run([python_bin, "-m", "venv", venv_dir], check=True)

    if IS_WINDOWS:
        pip_cmd = os.path.join(venv_dir, "Scripts", "pip")
        python_exe = os.path.join(venv_dir, "Scripts", "python.exe")
    else:
        pip_cmd = os.path.join(venv_dir, "bin", "pip")
        python_exe = os.path.join(venv_dir, "bin", "python")

    # pip 升级（pip>=25.3 要求通过 python -m pip 方式升级）
    subprocess.run([python_exe, "-m", "pip", "install", "--upgrade", "pip", "-q"], check=True)

    # CN 镜像检测
    pip_index_url = os.environ.get("PIP_INDEX_URL")
    if not pip_index_url and os.environ.get("TEST_AGENT_NO_CN_MIRROR", "0") != "1":
        tz = os.environ.get("TZ", "")
        if any([
            os.environ.get("LANG", "").startswith(("zh", "CN", "GB")),
            timezone_is_cn(),
        ]):
            print("→ 检测到 CN 环境, 用清华 PyPI 镜像加速")
            pip_index_url = "https://pypi.tuna.tsinghua.edu.cn/simple"
            pip_env = os.environ.copy()
            pip_env["PIP_INDEX_URL"] = pip_index_url
            pip_env["PIP_TRUSTED_HOST"] = "pypi.tuna.tsinghua.edu.cn"
        else:
            pip_env = os.environ.copy()
    else:
        pip_env = os.environ.copy()
        if pip_index_url:
            pip_env["PIP_INDEX_URL"] = pip_index_url

    print("→ 用 pip 装 Python 依赖 (首次约 5-15 min, CN 网已自动配清华镜像加速)...")

    req_file = os.path.join(project_root, "requirements.txt")
    if IS_WINDOWS:
        # Windows 跳过需 C 编译器的可选 image 包
        print("→ 检测到 Windows 环境, 跳过需 C 编译器的可选 image 包 (scikit-image / scikit-learn / opencv-python)")
        print("  如需视觉测试 (visual-test skill), 装 Visual Studio Build Tools 后手动: pip install scikit-image scikit-learn opencv-python")
        with open(req_file, encoding="utf-8") as f:
            lines = f.readlines()
        filtered = [l for l in lines if not l.startswith(("scikit-image", "scikit-learn", "opencv-python", "opencv-contrib-python"))]
        fd, tmp = tempfile.mkstemp(suffix=".txt", prefix="tagent-req-")
        with open(fd, "w", encoding="utf-8") as f:
            f.writelines(filtered)
        subprocess.run([pip_cmd, "install", "-r", tmp], env=pip_env, check=True)
        os.unlink(tmp)
    else:
        subprocess.run([pip_cmd, "install", "-r", req_file], env=pip_env, check=True)

    # Playwright 浏览器（按需安装，UI 测试才用）
    if IS_WINDOWS:
        playwright_cmd = os.path.join(venv_dir, "Scripts", "playwright.exe")
    else:
        playwright_cmd = os.path.join(venv_dir, "bin", "playwright")
    try:
        subprocess.run([playwright_cmd, "install", "chromium", "--with-deps"], check=True)
    except Exception:
        print(f"⚠️ Playwright 浏览器安装失败，如需 UI 测试请手动运行：{playwright_cmd} install chromium --with-deps")

    # 将 runtime 作为可编辑包安装到 venv（tagent 命令即可用）
    print("→ 安装 tagent CLI (pip install -e runtime/) ...")
    runtime_dir = os.path.join(project_root, "runtime")
    subprocess.run([pip_cmd, "install", "-e", runtime_dir], env=pip_env, check=True)


def _create_wrappers(project_root):
    """在项目根创建 tagent.bat / tagent 包装脚本，用户直接双击或用终端运行。"""
    if IS_WINDOWS:
        venv_python = os.path.join(project_root, ".venv", "Scripts", "python.exe")
        bat_path = os.path.join(project_root, "tagent.bat")
        with open(bat_path, "w", encoding="utf-8") as f:
            f.write(f'@echo off\nchcp 65001 > nul\n"{venv_python}" -m runtime.cli.main %*\nif "%1"=="" pause\n')
    else:
        venv_python = os.path.join(project_root, ".venv", "bin", "python")
        sh_path = os.path.join(project_root, "tagent")
        with open(sh_path, "w", encoding="utf-8") as f:
            f.write(f'#!/bin/sh\n"{venv_python}" -m runtime.cli.main "$@"\n')
        os.chmod(sh_path, 0o755)


def timezone_is_cn():
    """检测时区是否为中国（+0800）。"""
    import time
    return time.timezone == -28800


def finish(project_root):
    """打印完成提示。"""
    msg = f"""

{'=' * 50}
 ✅ 部署完成

 项目目录: {project_root}

 === 独立使用（不需 AI）===
   cd {project_root}
   .\tagent.bat                        # Windows 终端
   ./tagent                            # macOS / Linux 终端
   tagent run "path/to/prd.md"         # 一键执行
   tagent doctor                       # 健康检查
   tagent catalog                      # 查看所有专家和技能

 === AI 协作模式 ===
   1. 编辑 {project_root}/.env → 设 TAGENT_LLM_PROVIDER + API key
     内置: claude | openai | gemini | deepseek | qwen | ollama
     OpenAI 兼容: 智谱/豆包/Kimi/百川/讯飞 (设 TAGENT_LLM_API_BASE)
   2. cd {project_root} && claude      (或 cursor / Copilot / Windsurf)
   3. AI 会自动读取 CLAUDE.md，请确保它遵循 skills/ 流程文档

{'=' * 50}
"""
    print(msg)


def _rmtree_onerror(func, path, _exc_info):
    """Windows git objects are read-only, clear attribute before retry."""
    os.chmod(path, stat.S_IWRITE)
    func(path)


def _read_template_version(template_dir):
    """读取模板 VERSION 文件。"""
    vf = os.path.join(template_dir, "VERSION")
    if os.path.isfile(vf):
        with open(vf, encoding="utf-8") as f:
            return f.read().strip()
    return None


def _write_local_version(project_root, version):
    """写入 VERSION 文件供后续更新检测。"""
    vf = os.path.join(project_root, "VERSION")
    with open(vf, "w", encoding="utf-8") as f:
        f.write(version + "\n")


def _update_deps(project_root):
    """使用已有 venv 安装/更新 Python 依赖（不重建 venv）。"""
    if IS_WINDOWS:
        python_exe = os.path.join(project_root, ".venv", "Scripts", "python.exe")
        pip_cmd = os.path.join(project_root, ".venv", "Scripts", "pip")
    else:
        python_exe = os.path.join(project_root, ".venv", "bin", "python")
        pip_cmd = os.path.join(project_root, ".venv", "bin", "pip")

    if not os.path.isfile(python_exe):
        print("⚠️ 未找到虚拟环境，跳过依赖更新")
        return

    subprocess.run([python_exe, "-m", "pip", "install", "--upgrade", "pip", "-q"], check=True)

    # CN 镜像检测
    pip_env = os.environ.copy()
    if os.environ.get("TEST_AGENT_NO_CN_MIRROR", "0") != "1":
        if any([
            os.environ.get("LANG", "").startswith(("zh", "CN", "GB")),
            timezone_is_cn(),
        ]):
            pip_env["PIP_INDEX_URL"] = "https://pypi.tuna.tsinghua.edu.cn/simple"
            pip_env["PIP_TRUSTED_HOST"] = "pypi.tuna.tsinghua.edu.cn"

    req_file = os.path.join(project_root, "requirements.txt")
    print("→ 更新 Python 依赖...")
    if IS_WINDOWS:
        with open(req_file, encoding="utf-8") as f:
            lines = f.readlines()
        filtered = [l for l in lines if not l.startswith(("scikit-image", "scikit-learn", "opencv-python", "opencv-contrib-python"))]
        fd, tmp = tempfile.mkstemp(suffix=".txt", prefix="tagent-update-req-")
        with open(fd, "w", encoding="utf-8") as f:
            f.writelines(filtered)
        subprocess.run([pip_cmd, "install", "-r", tmp], env=pip_env, check=True)
        os.unlink(tmp)
    else:
        subprocess.run([pip_cmd, "install", "-r", req_file], env=pip_env, check=True)


def do_update():
    """轻量更新：克隆最新模板 → 比较版本 → 拷贝文件 → 更新依赖 → 保留用户数据。"""
    version_file = os.path.join(PROJECT_ROOT, "VERSION")
    legacy_file = os.path.join(PROJECT_ROOT, ".version")
    # Migration: rename legacy .version to VERSION if VERSION is missing
    if not os.path.isfile(version_file) and os.path.isfile(legacy_file):
        os.rename(legacy_file, version_file)
    if not os.path.isfile(version_file):
        print(f"❌ 未找到 VERSION 文件")
        print(f"   当前目录: {os.getcwd()}")
        print(f"   查找路径: {version_file}")
        print(f"   请先执行完整安装：python install.py <目录>")
        print(f"   或切换到项目目录后执行：cd <项目目录> && python install.py --update")
        sys.exit(1)

    with open(version_file, encoding="utf-8") as f:
        local_version = f.read().strip()

    print(f"→ 当前版本: {local_version}")

    template_dir_parent = tempfile.mkdtemp()
    template_dir = os.path.join(template_dir_parent, "Test-Agent")

    try:
        local_src = os.environ.get("TEST_AGENT_LOCAL_SRC")
        if local_src:
            print(f"→ [dev mode] 复制本地源代码: {local_src} → {template_dir}")
            shutil.copytree(local_src, template_dir)
        else:
            print("→ 检查更新...")
            subprocess.run(
                ["git", "clone", "--depth", "1", "--branch", REPO_BRANCH, REPO_URL, template_dir],
                check=True,
            )

        remote_version = _read_template_version(template_dir)
        if remote_version is None:
            print("❌ 无法读取远程版本信息")
            sys.exit(1)

        if local_version == remote_version:
            print(f"✓ 已是最新版本 ({local_version})")
            return

        print(f"→ 新版本可用: {local_version} → {remote_version}")
        print("→ 开始轻量更新（保留用户数据和 .venv）...")

        # 备份用户数据
        backed = backup_user_data(PROJECT_ROOT)

        # 拷贝新文件（跳过 create_dirs / setup_venv / claude code 安装）
        copy_agents(template_dir, PROJECT_ROOT)
        copy_skills(template_dir, PROJECT_ROOT)
        copy_config(template_dir, PROJECT_ROOT)
        copy_utils(template_dir, PROJECT_ROOT)
        copy_runtime(template_dir, PROJECT_ROOT)
        copy_ci(template_dir, PROJECT_ROOT)
        copy_top_level_docs(template_dir, PROJECT_ROOT)

        # 恢复用户数据
        restore_user_data(PROJECT_ROOT, backed)

        # 更新依赖
        _update_deps(PROJECT_ROOT)

        # 重建包装脚本
        _create_wrappers(PROJECT_ROOT)

        # 写回新版本号
        _write_local_version(PROJECT_ROOT, remote_version)

        # Post-update verification: real checks, no network, no fixtures
        # 3 real verifications that always work:
        print()
        print("→ 更新后验证...")
        verify_ok = True

        # [1] pip check — dependency integrity
        print("  [1/3] pip check...")
        r = subprocess.run([sys.executable, "-m", "pip", "check"], capture_output=True, text=True)
        if r.returncode == 0:
            print("  ✓ 依赖无冲突")
        else:
            print(f"  ⚠ 依赖冲突: {r.stderr.strip()[:200]}")
            verify_ok = False

        # [2] import check — runtime can be loaded
        print("  [2/3] runtime 导入 + catalog...")
        import_ok = subprocess.run(
            [sys.executable, "-c",
             "from runtime.cli.main import app; from runtime.registry.registry import build_catalog; "
             "cat=build_catalog(); n=len(cat.experts)+len(cat.skills); "
             "print(f'catalog={n} entries ({len(cat.experts)}e+{len(cat.skills)}s)')"],
            capture_output=True, text=True, cwd=PROJECT_ROOT,
        )
        if import_ok.returncode == 0:
            print(f"  ✓ {import_ok.stdout.strip()}")
        else:
            print(f"  ⚠ 导入失败: {import_ok.stderr.strip()[:200]}")
            verify_ok = False

        # [3] agent/skill files present — informational, not assertion
        print("  [3/3] 文件完整性...")
        agents_n = len(glob.glob(os.path.join(PROJECT_ROOT, DEPLOY_EXPERTS_DIR, "[0-9]*.md")))
        skills_n = len(glob.glob(os.path.join(PROJECT_ROOT, DEPLOY_SKILLS_DIR, "*.md")))
        print(f"  ✓ agents={agents_n}, skills={skills_n}")

        print("=" * 50)
        if verify_ok:
            print(f" ✅ 已更新到 {remote_version} (验证通过)")
        else:
            print(f" ⚠ 已更新到 {remote_version} (验证未通过)")
            print("   回滚: 从 workspace/backup/ 恢复, 或 git checkout <旧版本>")
        print("=" * 50)

    finally:
        if os.path.isdir(template_dir_parent):
            shutil.rmtree(template_dir_parent, onerror=_rmtree_onerror)
        # cleanup backup tmp if any leftover (restore_user_data usually handles this)
        # handled in finally block of main, but do_update has its own finally


def main():
    banner()

    if UPDATE_MODE:
        do_update()
        return

    # 1. 检查 + 自动安装前置工具
    ensure_prerequisites()
    python_bin = find_python()
    print(f"→ 使用 Python: {python_bin}")

    # 2. 幂等备份
    backed = backup_user_data(PROJECT_ROOT)

    template_dir_parent = tempfile.mkdtemp()
    template_dir = os.path.join(template_dir_parent, "Test-Agent")

    try:
        # 3. 获取模板
        local_src = os.environ.get("TEST_AGENT_LOCAL_SRC")
        if local_src:
            print(f"→ [dev mode] 复制本地源代码: {local_src} → {template_dir}")
            shutil.copytree(local_src, template_dir)
        else:
            print(f"→ 从 GitHub 克隆模板...")
            print(f"   {REPO_URL} ({REPO_BRANCH})")
            try:
                subprocess.run(
                    ["git", "clone", "--depth", "1", "--branch", REPO_BRANCH, REPO_URL, template_dir],
                    check=True, timeout=120,
                )
            except subprocess.TimeoutExpired:
                print("❌ Git 克隆超时（>120 秒），请检查网络或使用本地模式：")
                print(f"   set TEST_AGENT_LOCAL_SRC={os.getcwd()}")
                print(f"   python install.py <目标目录>")
                sys.exit(1)
            except subprocess.CalledProcessError as e:
                print(f"❌ Git 克隆失败: {e}")
                print(f"   仓库: {REPO_URL}")
                print(f"   可以尝试本地模式：set TEST_AGENT_LOCAL_SRC={os.getcwd()}")
                sys.exit(1)

        # 4. 安装 Claude Code
        if shutil.which("claude") is None:
            print("→ 安装 Claude Code...")
            subprocess.run(["npm", "install", "-g", "@anthropic-ai/claude-code"], check=True)

        # 5. 创建目录结构
        create_dirs(PROJECT_ROOT)

        # 6. 拷贝文件
        copy_agents(template_dir, PROJECT_ROOT)
        copy_skills(template_dir, PROJECT_ROOT)
        copy_config(template_dir, PROJECT_ROOT)
        copy_utils(template_dir, PROJECT_ROOT)
        copy_runtime(template_dir, PROJECT_ROOT)
        copy_ci(template_dir, PROJECT_ROOT)
        copy_top_level_docs(template_dir, PROJECT_ROOT)

        # 7. Python 虚拟环境 + 依赖 + tagent CLI
        setup_venv(python_bin, PROJECT_ROOT)

        # 8. 创建 tagent.bat / tagent 包装脚本
        _create_wrappers(PROJECT_ROOT)

        # 10. 恢复用户数据
        restore_user_data(PROJECT_ROOT, backed)

        # 11. 写入 VERSION 供后续更新检测
        version = _read_template_version(template_dir)
        if version:
            _write_local_version(PROJECT_ROOT, version)

        finish(PROJECT_ROOT)

    except Exception as e:
        print(f"\n❌ 部署失败: {e}")
        import traceback
        traceback.print_exc()

    finally:
        # 清理临时目录
        if os.path.isdir(template_dir_parent):
            shutil.rmtree(template_dir_parent, onerror=_rmtree_onerror)
        tmp = backed.pop("__tmp__", None)
        if tmp and os.path.isdir(tmp):
            shutil.rmtree(tmp, onerror=_rmtree_onerror)

    # 保持窗口打开，成功或失败用户都能看到结果
    if IS_WINDOWS and not UPDATE_MODE:
        input("\n按 Enter 键退出...")


if __name__ == "__main__":
    main()
