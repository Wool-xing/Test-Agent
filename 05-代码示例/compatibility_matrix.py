"""
兼容性矩阵：浏览器 / OS / 分辨率 / 移动设备 / 语言
被引用方：06-自动化脚本 + 10-移动测试 + visual-tester
"""
import logging
from itertools import product
from typing import Dict, List

logger = logging.getLogger(__name__)


# ===== 默认矩阵（项目可覆盖）=====

WEB_BROWSERS = ["chromium", "firefox", "webkit"]

WEB_RESOLUTIONS = [
    {"width": 1920, "height": 1080, "name": "FullHD"},
    {"width": 1366, "height": 768, "name": "Laptop"},
    {"width": 768, "height": 1024, "name": "iPad"},
    {"width": 375, "height": 667, "name": "iPhone6"},
    {"width": 360, "height": 800, "name": "Android"},
]

MOBILE_DEVICES_ANDROID = [
    {"device": "Pixel 6 Pro", "android": "14"},
    {"device": "Galaxy S23", "android": "13"},
    {"device": "Xiaomi 12", "android": "12"},
]

MOBILE_DEVICES_IOS = [
    {"device": "iPhone 15 Pro", "ios": "17.2"},
    {"device": "iPhone 14", "ios": "16.5"},
    {"device": "iPad Air", "ios": "17.0"},
]

LANGUAGES = ["zh-CN", "en-US", "ja-JP", "ko-KR"]


# ===== 矩阵生成 =====

def web_matrix(browsers: List[str] = None, resolutions: List[Dict] = None,
                languages: List[str] = None) -> List[Dict]:
    """生成 Web 兼容性矩阵"""
    return [
        {"browser": b, "resolution": r, "language": l}
        for b, r, l in product(browsers or WEB_BROWSERS,
                                resolutions or WEB_RESOLUTIONS,
                                languages or [LANGUAGES[0]])
    ]


def mobile_matrix(platform: str = "android") -> List[Dict]:
    return MOBILE_DEVICES_ANDROID if platform == "android" else MOBILE_DEVICES_IOS


# ===== pytest 参数化辅助 =====

def to_pytest_params(matrix: List[Dict]) -> List:
    """转 pytest.mark.parametrize 兼容格式"""
    keys = list(matrix[0].keys()) if matrix else []
    values = [tuple(m[k] for k in keys) for m in matrix]
    return keys, values


# ===== Playwright 跨浏览器 fixture 模板 =====

PLAYWRIGHT_FIXTURE = '''
# conftest.py 加（按需）：
import pytest
from playwright.sync_api import sync_playwright

@pytest.fixture(params=["chromium", "firefox", "webkit"])
def cross_browser(request):
    with sync_playwright() as p:
        browser = getattr(p, request.param).launch(headless=True)
        yield browser
        browser.close()
'''


# ===== CI matrix（GitHub Actions YAML 片段）=====

GH_ACTIONS_BROWSER_MATRIX = """
strategy:
  matrix:
    browser: [chromium, firefox, webkit]
    resolution: [{width: 1920, height: 1080}, {width: 375, height: 667}]
runs-on: ubuntu-latest
"""

GH_ACTIONS_OS_MATRIX = """
strategy:
  matrix:
    os: [ubuntu-latest, macos-latest, windows-latest]
runs-on: ${{ matrix.os }}
"""


# ===== CLI =====

if __name__ == "__main__":
    import argparse
    import json
    parser = argparse.ArgumentParser(description="兼容性矩阵生成")
    parser.add_argument("--type", choices=["web", "android", "ios"], default="web")
    args = parser.parse_args()
    if args.type == "web":
        print(json.dumps(web_matrix(), indent=2, ensure_ascii=False))
    else:
        print(json.dumps(mobile_matrix(args.type), indent=2, ensure_ascii=False))
