"""
API 调用工具 - 指数退避重试
权威重试策略：base_delay=10s, max_delay=60s, max_retries=3
  第1次失败 → 等待10s
  第2次失败 → 等待20s
  第3次失败 → 等待40s
  第4次仍失败 → 抛出异常

被引用方：08-bug-manager / zentao_bug_manager.py / agent 内任意 API 调用
"""
import logging
import time
from email.utils import parsedate_to_datetime
from typing import Any, Callable, Optional, Tuple, Type

import requests
from tenacity import (
    before_sleep_log,
    retry,
    retry_if_exception_type,
    stop_after_attempt,
    wait_exponential,
)

logger = logging.getLogger(__name__)


def _parse_retry_after(value: str, default: float) -> float:
    """Retry-After 支持秒数 或 HTTP-date。"""
    try:
        return float(value)
    except (TypeError, ValueError):
        pass
    try:
        dt = parsedate_to_datetime(value)
        if dt:
            from datetime import datetime, timezone
            now = datetime.now(timezone.utc) if dt.tzinfo else datetime.utcnow()
            delta = (dt - now).total_seconds()
            return max(0.0, delta)
    except Exception:
        pass
    return default


# ===== 方式1（推荐）：通用包装器 =====

def call_with_retry(
    func: Callable,
    *args,
    max_retries: int = 3,
    base_delay: float = 10.0,
    max_delay: float = 60.0,
    retryable_exceptions: Tuple[Type[Exception], ...] = (Exception,),
    retryable_status_codes: Tuple[int, ...] = (429, 500, 502, 503, 504),
    **kwargs,
) -> Any:
    """
    通用重试包装器（指数退避）。
    delay = min(base_delay * 2^attempt, max_delay)，10/20/40s 序列受 max_delay 截断。
    """
    last_exception: Optional[BaseException] = None

    for attempt in range(max_retries + 1):
        try:
            result = func(*args, **kwargs)
            if hasattr(result, "status_code") and result.status_code in retryable_status_codes:
                raise requests.exceptions.HTTPError(
                    f"HTTP {result.status_code}", response=result
                )
            return result

        except retryable_exceptions as e:
            last_exception = e
            if attempt >= max_retries:
                logger.error(f"已达最大重试次数 ({max_retries})，最终失败: {e}")
                break

            delay = min(base_delay * (2 ** attempt), max_delay)

            # 速率限制时使用 Retry-After 头
            if hasattr(e, "response") and e.response is not None:
                ra = e.response.headers.get("Retry-After")
                if ra is not None:
                    delay = max(delay, _parse_retry_after(ra, delay))

            logger.warning(
                f"调用失败 (尝试 {attempt + 1}/{max_retries + 1})，"
                f"等待 {delay:.0f}s 后重试: {type(e).__name__}: {e}"
            )
            time.sleep(delay)

    assert last_exception is not None
    raise last_exception


# ===== 方式2：tenacity 装饰器（备选）=====

@retry(
    stop=stop_after_attempt(4),  # 1 次首发 + 3 次重试
    wait=wait_exponential(multiplier=10, min=10, max=60),  # 10s/20s/40s
    retry=retry_if_exception_type((
        requests.exceptions.Timeout,
        requests.exceptions.ConnectionError,
        requests.exceptions.HTTPError,
    )),
    before_sleep=before_sleep_log(logger, logging.WARNING),
)
def api_call_with_exponential_backoff(
    url: str,
    method: str = "GET",
    session: Optional[requests.Session] = None,
    **kwargs,
) -> requests.Response:
    """
    tenacity 装饰器版本。复用 session（连接池/Cookie），不每次新建。
    multiplier=10, min=10, max=60 → 等待序列 10s/20s/40s（与 call_with_retry 同步）。
    """
    s = session or requests.Session()
    response = s.request(method, url, timeout=30, **kwargs)

    if response.status_code == 429:
        ra = response.headers.get("Retry-After", "10")
        delay = _parse_retry_after(ra, 10.0)
        logger.warning(f"触发速率限制，等待 {delay:.0f}s 后重试")
        time.sleep(delay)
        response.raise_for_status()  # 触发 HTTPError 让 tenacity 重试

    response.raise_for_status()
    return response


# ===== 方式3：异步版本（高并发）=====

async def async_api_call_with_retry(
    url: str,
    method: str = "GET",
    max_retries: int = 3,
    base_delay: float = 10.0,
    max_delay: float = 60.0,
    **kwargs,
):
    """
    异步重试。返回 httpx.Response（与同步版返回类型对齐：均为 response 对象）。
    """
    import asyncio

    import httpx

    last_exc: Optional[BaseException] = None
    async with httpx.AsyncClient(timeout=30) as client:
        for attempt in range(max_retries + 1):
            try:
                response = await client.request(method, url, **kwargs)
                response.raise_for_status()
                return response
            except (httpx.HTTPStatusError, httpx.TransportError) as e:
                last_exc = e
                if attempt >= max_retries:
                    raise
                delay = min(base_delay * (2 ** attempt), max_delay)
                logger.warning(f"异步请求失败 (尝试 {attempt + 1})，等待 {delay:.0f}s: {e}")
                await asyncio.sleep(delay)

    assert last_exc is not None
    raise last_exc


# ===== 示例 =====

if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)

    # 示例 1：禅道 Bug 提交
    def submit_bug_example():
        from zentao_bug_manager import ZentaoBugManager
        client = ZentaoBugManager()
        return call_with_retry(
            client.create_bug,
            {"title": "测试Bug", "product": 1, "steps": "..."},
            max_retries=3,
            base_delay=10,
        )

    # 示例 2：接口探活（带重试）
    response = call_with_retry(
        requests.get,
        "http://test-api.example.com/health",
        max_retries=3,
        retryable_status_codes=(429, 500, 502, 503, 504),
    )
    print(f"接口响应: {response.status_code}")
