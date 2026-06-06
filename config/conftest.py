"""
pytest 全局配置文件 - conftest.py
放置于项目根目录（直接可用，无外部依赖）。
"""
import json
import logging
import os
import sys
from dataclasses import dataclass, field
from datetime import datetime
from pathlib import Path
from typing import Optional

import pytest
from dotenv import load_dotenv

# 加载环境变量
load_dotenv()

logger = logging.getLogger(__name__)

# 注入 utils 包 + utils 内部模块 到 sys.path
# 部署后: conftest.py 在 $PROJECT_ROOT/, utils 在 $PROJECT_ROOT/utils/
# 源码仓: conftest.py 在 config/, utils 在 ../utils/
# 双场景都加 sys.path,确保 utils 平铺 import (e.g., `from api_retry_util import ...`) 工作
_CONFIG_DIR = Path(__file__).parent
_PROJECT_ROOT = _CONFIG_DIR.parent if (_CONFIG_DIR / ".." / "utils").resolve().is_dir() else _CONFIG_DIR
if str(_CONFIG_DIR) not in sys.path:
    sys.path.insert(0, str(_CONFIG_DIR))
if str(_PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(_PROJECT_ROOT))

_UTILS_CANDIDATES = [
    _PROJECT_ROOT / "utils",                # 部署后路径
    _PROJECT_ROOT.parent / "utils",    # 源码仓路径
]
for _utils_dir in _UTILS_CANDIDATES:
    if _utils_dir.is_dir() and str(_utils_dir) not in sys.path:
        sys.path.insert(0, str(_utils_dir))
        # utils 子目录也注入 — V1.x 重组后 utils/ 下 12 子目录
        for _sub in _utils_dir.iterdir():
            if _sub.is_dir() and not _sub.name.startswith(("_", ".")):
                if str(_sub) not in sys.path:
                    sys.path.insert(0, str(_sub))


# ===== 输出路径：按项目归类（委托 utils/paths.py）=====

from utils.paths import get_project_name, get_output_dir, current_run_id


# ===== 环境配置 =====

@dataclass
class EnvConfig:
    env_name: str
    app_base_url: str
    api_base_url: str
    db_host: str
    db_port: int = 5432
    db_name: str = ""
    db_user: str = ""
    db_password: str = ""
    redis_host: str = "localhost"
    redis_port: int = 6379
    zentao_url: str = ""
    mock_server_url: str = ""


def get_current_env() -> EnvConfig:
    """根据 TEST_ENV 环境变量返回对应配置（test/staging）。未知环境直接 raise，禁止 prod。"""
    env = os.getenv("TEST_ENV", "test").lower()
    if env == "prod":
        raise ValueError("禁止以 prod 作为测试环境（防止误测生产）")

    if env == "test":
        return EnvConfig(
            env_name="test",
            app_base_url=os.getenv("TEST_APP_URL", "http://test.example.com"),
            api_base_url=os.getenv("TEST_API_URL", "http://test-api.example.com"),
            db_host=os.getenv("TEST_DB_HOST", "localhost"),
            db_port=int(os.getenv("TEST_DB_PORT", "5432")),
            db_name=os.getenv("TEST_DB_NAME", ""),
            db_user=os.getenv("TEST_DB_USER", ""),
            db_password=os.getenv("TEST_DB_PASSWORD", ""),
            redis_host=os.getenv("TEST_REDIS_HOST", "localhost"),
            redis_port=int(os.getenv("TEST_REDIS_PORT", "6379")),
            zentao_url=os.getenv("TEST_ZENTAO_URL", os.getenv("ZENTAO_BASE_URL", "")),
            mock_server_url=os.getenv("MOCK_SERVER_URL", ""),
        )
    if env == "staging":
        return EnvConfig(
            env_name="staging",
            app_base_url=os.getenv("STAGING_APP_URL", "http://staging.example.com"),
            api_base_url=os.getenv("STAGING_API_URL", "http://staging-api.example.com"),
            db_host=os.getenv("STAGING_DB_HOST", "localhost"),
            db_port=int(os.getenv("STAGING_DB_PORT", "5432")),
            db_name=os.getenv("STAGING_DB_NAME", ""),
            db_user=os.getenv("STAGING_DB_USER", ""),
            db_password=os.getenv("STAGING_DB_PASSWORD", ""),
            redis_host=os.getenv("STAGING_REDIS_HOST", "localhost"),
            redis_port=int(os.getenv("STAGING_REDIS_PORT", "6379")),
            zentao_url=os.getenv("STAGING_ZENTAO_URL", os.getenv("ZENTAO_BASE_URL", "")),
            mock_server_url=os.getenv("MOCK_SERVER_URL", ""),
        )
    raise ValueError(f"未知的测试环境: {env}，可选值: test/staging")


# ===== 环境配置 Fixture =====

@pytest.fixture(scope="session")
def env_config() -> EnvConfig:
    """会话级环境配置"""
    config = get_current_env()
    logger.info(f"测试环境: {config.env_name} - {config.app_base_url}")
    return config


@pytest.fixture(scope="function")
def test_data(env_config: EnvConfig, tmp_path: Path) -> dict:
    """
    函数级测试数据。优先读取 workspace/测试数据/test_data.json；
    不存在则尝试调用 utils.data_factory 生成基础数据。
    每个测试独立 tmp_path，避免并行文件冲突。
    """
    data_file = Path("workspace/测试数据/test_data.json")
    if data_file.exists():
        with open(data_file, encoding="utf-8") as f:
            return json.load(f)

    # 尝试用 data_factory 生成
    try:
        from data_factory import TestDataManager
        mgr = TestDataManager(env_config)
        data = {
            "normal_user": mgr.create_test_user(status="active"),
            "admin_user": mgr.create_test_user(status="active", role="admin"),
            "locked_user": mgr.create_test_user(status="locked"),
        }
    except Exception as e:
        logger.warning(f"data_factory 不可用，回退到 .env 兜底数据: {e}")
        data = {
            "normal_user": {
                "username": os.getenv("TEST_USER", "testuser@example.com"),
                "password": os.getenv("TEST_PASS", ""),
                "display_name": "测试用户",
            },
            "admin_user": {
                "username": os.getenv("ADMIN_USER", "admin@example.com"),
                "password": os.getenv("ADMIN_PASS", ""),
                "display_name": "管理员",
            },
        }

    # 写入 tmp_path 避免并行测试文件冲突
    tmp_data_file = tmp_path / "test_data.json"
    with open(tmp_data_file, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)
    logger.info(f"已写入测试数据: {tmp_data_file}")
    return data


# ===== Playwright 浏览器 Fixture（lazy import 避免纯 API 测试加载 playwright）=====

@pytest.fixture(scope="function")
def browser_context(env_config: EnvConfig):
    from playwright.sync_api import sync_playwright

    with sync_playwright() as p:
        browser = p.chromium.launch(
            headless=os.getenv("HEADLESS", "true").lower() == "true",
            args=["--no-sandbox", "--disable-dev-shm-usage"],
        )
        context = browser.new_context(
            base_url=env_config.app_base_url,
            viewport={"width": 1920, "height": 1080},
            locale="zh-CN",
            timezone_id="Asia/Shanghai",
        )
        context.set_default_timeout(30000)
        yield context
        context.close()
        browser.close()


@pytest.fixture(scope="function")
def page(browser_context):
    """函数级页面（每个测试用例独立页面）"""
    p = browser_context.new_page()
    yield p
    p.close()


# ===== HTTP 客户端 Fixture =====

@pytest.fixture(scope="session")
def api_client(env_config: EnvConfig):
    """会话级 API 客户端（urllib3 Retry：1s/2s/4s）"""
    import requests
    from requests.adapters import HTTPAdapter
    from urllib3.util.retry import Retry

    session = requests.Session()
    retry_strategy = Retry(
        total=3,
        backoff_factor=1.0,
        status_forcelist=[429, 500, 502, 503, 504],
        allowed_methods=["HEAD", "GET", "POST", "PUT", "DELETE", "OPTIONS"],
    )
    adapter = HTTPAdapter(max_retries=retry_strategy)
    session.mount("http://", adapter)
    session.mount("https://", adapter)

    session.base_url = env_config.api_base_url
    # Content-Type 不在 session 默认设置，按 per-request 传（GET 不应带）
    session.headers.update({
        "Accept": "application/json",
        "X-Test-Session": f"test-{datetime.now().strftime('%Y%m%d%H%M%S')}",
    })
    return session


# ===== 数据清理 Fixture =====

@pytest.fixture(scope="function", autouse=True)
def cleanup_tracker():
    """函数级清理追踪器（每个测试用例自动执行清理）"""
    cleanup_tasks = []

    def register(func, *args, **kwargs):
        cleanup_tasks.append((func, args, kwargs))

    yield register

    for func, args, kwargs in reversed(cleanup_tasks):
        try:
            func(*args, **kwargs)
        except Exception as e:
            logger.warning(f"清理任务失败（不影响测试结果）: {e}")


# ===== 测试报告增强：失败时自动截图（含 setup/teardown）=====

@pytest.hookimpl(hookwrapper=True)
def pytest_runtest_makereport(item, call):
    outcome = yield
    rep = outcome.get_result()

    if rep.failed and rep.when in ("setup", "call", "teardown"):
        if "page" in item.fixturenames:
            try:
                page = item.funcargs.get("page")
                if page:
                    screenshot_dir = get_output_dir("screenshots", current_run_id())
                    screenshot_dir.mkdir(parents=True, exist_ok=True)
                    fname = f"{item.name}_{rep.when}_{datetime.now().strftime('%H%M%S')}.png"
                    page.screenshot(path=str(screenshot_dir / fname))
                    logger.info(f"失败截图: {screenshot_dir / fname}")
            except Exception as e:
                logger.warning(f"截图失败: {e}")


# ===== 初始化：创建所有 workflow 产出目录 =====

_DIRS_INITIALIZED = False


def pytest_configure(config):
    """首次运行创建产出目录；已存在则跳过（性能优化）"""
    global _DIRS_INITIALIZED
    if _DIRS_INITIALIZED:
        return

    # 标记文件：存在则跳过 mkdir（首次后第二次启动免 80+ 次 mkdir 调用）
    sentinel = Path(".pytest_cache/.workflow_dirs_init")
    if sentinel.exists():
        _DIRS_INITIALIZED = True
        return

    project = get_project_name()
    workflow_dirs = [
        "workspace/测试计划",
        "workspace/需求分析",
        "workspace/测试用例",
        "workspace/测试数据",
        "workspace/自动化脚本/python",
        "workspace/自动化脚本/jmeter",
        # 项目级持久目录（跨 run 共享）
        f"workspace/测试报告/{project}/baselines",
        f"workspace/测试报告/{project}/history",
        "workspace/自动化脚本/python/features",
        "workspace/自动化脚本/python/i18n",
        "workspace/自动化脚本/python/pacts",
    ]
    for d in workflow_dirs:
        Path(d).mkdir(parents=True, exist_ok=True)

    # 标记已初始化
    sentinel.parent.mkdir(parents=True, exist_ok=True)
    sentinel.touch()
    _DIRS_INITIALIZED = True


@pytest.fixture(scope="session", autouse=True)
def session_setup_teardown(env_config: EnvConfig):
    logger.info(f"=== 测试会话开始: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')} ===")
    logger.info(f"测试环境: {env_config.env_name} | 应用: {env_config.app_base_url}")
    yield
    logger.info(f"=== 测试会话结束: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')} ===")
