# Phase 3 实施细节：引擎加固

> 每项含：具体文件·行号·改动·风险·验证方式

---

## #9 自愈引擎（Self-Healing）

### 风险：低。纯新增模块，不改现有逻辑

### 新建文件

**`runtime/self_healing/__init__.py`**
```python
"""Self-healing: auto-retry + locator fallback + LLM output repair."""
from runtime.self_healing.retry import with_retry
from runtime.self_healing.locator_store import LocatorStore
```

**`runtime/self_healing/retry.py`**
- `with_retry(func, max_retries=3, backoff=2.0)` — 装饰器/包装器
- 捕获 `subprocess.TimeoutExpired` / `RuntimeError` / `LLMError`
- 按指数退避重试，每次重试前调 healer 刷新状态
- 重试耗尽后抛出原始异常

**`runtime/self_healing/locator_store.py`**
- `LocatorStore` 类：多属性元素定位存储
- `add(name, primary, fallbacks: list)` — 注册定位器
- `resolve(name)` → 返回当前可用定位器链
- 支持 JSON 文件持久化（可选）

### 修改文件

**`runtime/orchestrator/adapters/scripts.py:49-56`**
- `run_script()` 调用外包 `with_retry()`
- 风险：中。改脚本执行路径
- 验证：现有 128 tests 全部通过

**`runtime/orchestrator/direct.py:71-78`**
- `_run_node()` 调用外包 `with_retry()`
- 风险：中。见 #10

### 改动量：~120 行新增，~10 行修改

---

## #10 Direct Executor 零重试

### 风险：中。改核心执行路径，需全量测试

### 修改文件

**`runtime/orchestrator/direct.py:71-78`**
```python
# BEFORE (line 71-78):
try:
    results[next_id] = futures[next_id].result()
    if not results[next_id].get("ok"):
        failures.append(next_id)
except Exception as e:
    log.error("node {} crashed: {}", next_id, e)
    results[next_id] = {"id": next_id, "ok": False, "error": str(e)}
    failures.append(next_id)

# AFTER:
try:
    results[next_id] = futures[next_id].result()
except Exception as e:
    log.warning("node {} attempt failed: {}", next_id, e)
    # retry up to 2 more times with backoff
    for attempt in range(2):
        time.sleep(2 ** attempt)
        try:
            fut = pool.submit(_run_node, by_id[next_id])
            results[next_id] = fut.result()
            break
        except Exception:
            log.warning("node {} retry {}/2 failed", next_id, attempt + 1)
            if attempt == 1:
                results[next_id] = {"id": next_id, "ok": False, "error": str(e)}
                failures.append(next_id)
if not results[next_id].get("ok"):
    failures.append(next_id)
```

**同样改 `direct.py:82-89`（done_now 路径）**

### 验证：`test_execute_node_allows_production_skill` + smoke e2e

---

## #11 on_failure="skip" 空实现

### 风险：低。Bug fix，不改 API

### 修改文件

**`runtime/orchestrator/tasks.py:38-39`**
```python
# BEFORE:
if not outcome.ok:
    logger.warning("node {} failed (on_failure={}): {}", node.id, node.on_failure, ...)
return summary  # ← 失败节点仍计入 failures

# AFTER:
if not outcome.ok:
    if node.on_failure == "skip":
        summary["skipped"] = True
        logger.info("node {} skipped per on_failure=skip", node.id)
    else:
        logger.warning("node {} failed (on_failure={}): {}", node.id, node.on_failure, ...)
return summary
```

**`runtime/orchestrator/flows.py:36-44`**
```python
# 加 skip 计数
for nid, fut in futures.items():
    try:
        results[nid] = fut.result()
        if results[nid].get("skipped"):
            skipped.append(nid)  # NEW
        elif not results[nid].get("ok"):
            failures.append(nid)
    ...
```

**`runtime/orchestrator/direct.py:94-98`**
```python
# rollout_skipped 扩展为通用 skip
skipped = [
    nid for nid, r in results.items()
    if r.get("skipped") or ("[V1.x rollout]" in (r.get("stderr_tail") or ""))
]
```

### 验证：新增 `test_on_failure_skip` 测试

---

## #12 共享 fixture 阻塞并行

### 风险：低。仅改测试 conftest，不影响生产代码

### 修改文件

**`runtime/tests/conftest.py:106`**
```python
# BEFORE:
@pytest.fixture(scope="session")
def test_data(tmp_path_factory):

# AFTER:
@pytest.fixture()  # function scope default
def test_data(tmp_path):
```

**`runtime/tests/conftest.py:150`**
```python
# BEFORE:
@pytest.fixture(scope="session")
def browser_context():

# AFTER:
@pytest.fixture()  # function scope
def browser_context():
```
- 每个测试独立 tmp_path，无文件冲突
- 风险：并行数高时资源消耗增加（但测试套件本身不大）

### 验证：`pytest -n auto` 并行执行无冲突

---

## #13 DAG 执行进度 + 断路器

### 风险：中。改 Prefect flow + direct executor 执行流程

### 修改文件

**`runtime/orchestrator/flows.py:36`**
```python
# 加：
from tqdm import tqdm

MAX_FAILURES = 3  # 断路器阈值

# 执行循环改为：
failures = []
for nid, fut in tqdm(futures.items(), desc="DAG nodes"):
    try:
        results[nid] = fut.result()
        if not results[nid].get("ok") and not results[nid].get("skipped"):
            failures.append(nid)
            if len(failures) >= MAX_FAILURES:
                log.error("circuit breaker: {} failures, aborting", len(failures))
                break
    except Exception as e:
        ...
```

**`runtime/orchestrator/direct.py:57`**
```python
# 加同逻辑：
MAX_FAILURES = 3
# 在 failures.append() 后加断路器检查
if len(failures) >= MAX_FAILURES:
    log.error("circuit breaker: aborting DAG")
    break
```

**`runtime/orchestrator/tasks.py:14`**
```python
# BEFORE:
@task(retries=2, retry_delay_seconds=exponential_backoff(backoff_factor=5))

# AFTER:
@task(retries=2, retry_delay_seconds=exponential_backoff(backoff_factor=5),
      timeout_seconds=3600)  # DAG 级超时: 1 小时
```

### 验证：构造一个 4 连败的 DAG，确认断路器在 3 次后触发

---

## 改动汇总

| # | 新建 | 修改 | 行数 | 风险 | 状态 |
|---|------|------|------|------|------|
| 9 | 3 文件 | 2 文件 | +120, ~10 | 低 | ✅ done |
| 10 | 0 | 1 文件(direct.py) | ~30 | 中 | ✅ done |
| 11 | 0 | 3 文件(tasks/flows/direct) | ~20 | 低 | ✅ done |
| 12 | 0 | 1 文件(04-配置文件/conftest.py) | ~5 | 低 | ✅ done |
| 13 | 0 | 3 文件(flows/direct/tasks) | ~25 | 中 | ✅ done |
| **合计** | **3** | **6 (实际7)** | **~210** | | **5/5 done** |

---

## 执行顺序

```
#12 (fixture scope, 纯测试, 1分钟) →
#11 (skip bugfix, 5分钟) →
#9  (self-healing 基础设施, 15分钟) →
#10 (direct retry, 接 #9 的 retry wrapper, 10分钟) →
#13 (进度+断路器, 10分钟)
```

## 验证链

每个修复完成 → `pytest runtime/tests/ -q` → 148 passed
全部完成 → `tagent demo -y` → 9/9 DAG ok

---

## 实施记录 (2026-05-17)

**#12** `04-配置文件/conftest.py`: `test_data` scope=session→function + tmp_path, `browser_context` scope=session→function. 消除并行文件冲突.
**#11** `tasks.py` + `flows.py` + `direct.py`: on_failure=skip 节点设 summary.skipped=True, 不计入 failures. skipped 独立追踪.
**#9** 新建 `runtime/self_healing/` (retry.py + locator_store.py + __init__.py). `scripts.py` subprocess.run 外包 with_retry. `direct.py` _run_node execute_node 外包 with_retry. 指数退避 3 次重试.
**#10** `direct.py` 阻塞路径 + done_now 路径: 异常时 resubmit _run_node 最多 2 次, 指数退避 2^attempt 秒.
**#13** `flows.py` + `direct.py`: MAX_FAILURES=3 断路器, 达阈值停止提交/break. `tasks.py`: timeout_seconds=3600. 进度日志每节点完成输出.

全部 148 tests pass.
