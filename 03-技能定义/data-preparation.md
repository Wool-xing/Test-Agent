---
name: data-preparation
description: 测试数据准备 Skill。自动生成、注入、清理测试数据（含 JMeter 参数化 CSV），支持边界值/异常值/批量场景。所有实现位于 utils/data_factory.py / utils/data_masking.py / utils/jmeter_csv_exporter.py。
tools: Read, Write, Bash, Grep, Glob
---

# 测试数据准备 Skill

> **目标**：测试执行前自动准备所有必要数据，测试结束后自动清理。

## 🔔 调用前置准备

```
□ env-manager 已通过基础健康检查（DB/Redis 可达）
□ .env 已填 TEST_DB_HOST / TEST_DB_USER / TEST_DB_PASSWORD / TEST_DB_NAME
□ pip 装 faker + factory-boy + SQLAlchemy
□ utils/data_factory.py + data_masking.py + jmeter_csv_exporter.py 已部署
□ 业务表 schema 已就绪（DB 写入需要）
□ 用例 Excel（用于分析数据需求，可选）
□ 性能场景需指定并发数（CSV 行数 = 并发数）
```

## 📋 执行流程

### 步骤1：分析数据需求

读取测试用例 Excel，提取数据需求。**注意：使用 03-用例设计 标准 Excel 16 列布局**：

```
列索引（1-based）：
1.用例ID  2.模块  3.类型  4.优先级  5.用例名称  6.前置条件
7.测试步骤  8.测试数据  9.预期结果  ...
```

实现：

```python
import logging
import re

import openpyxl

logger = logging.getLogger(__name__)


def analyze_data_requirements(test_cases_file: str) -> dict:
    """从测试用例 Excel 分析数据需求"""
    wb = openpyxl.load_workbook(test_cases_file)

    # 优先读取 'P0_P1回归集' Sheet（若存在），否则读 '测试用例'
    sheet_name = "P0_P1回归集" if "P0_P1回归集" in wb.sheetnames else "测试用例"
    ws = wb[sheet_name]

    requirements = {
        "users": [],
        "boundary_cases": [],
        "security_cases": [],
        "performance_data_count": 0,
    }

    for row in ws.iter_rows(min_row=2, values_only=True):
        if not row or not row[0]:
            continue
        precondition = str(row[5] or "")  # 第 6 列：前置条件（1-based 索引 6 → 0-based 5）
        case_type = str(row[2] or "")     # 类型（UI/API/PERF/SEC）
        case_data = str(row[7] or "")     # 测试数据

        if "用户" in precondition or "账号" in precondition:
            requirements["users"].append(precondition)

        # 并发数提取（regex 兼容 "5并发"/"50并发"/"1000并发"）
        m = re.search(r"(\d+)\s*并发", precondition + " " + case_data)
        if m:
            requirements["performance_data_count"] = max(
                requirements["performance_data_count"], int(m.group(1))
            )

        if case_type == "SEC":
            requirements["security_cases"].append(case_data)

    logger.info(f"数据需求分析完成: {requirements}")
    return requirements
```

### 步骤2：执行数据准备

```python
import json
from pathlib import Path

from data_factory import TestDataManager
from data_masking import DataMasker

# conftest 中的 EnvConfig（运行时由 pytest fixture 注入；独立运行时手动构造）
from conftest import get_current_env

env_config = get_current_env()
manager = TestDataManager(env_config)

# 准备基础测试账号
test_users = {
    "normal_user":   manager.create_test_user(status="active", role="user"),
    "admin_user":    manager.create_test_user(status="active", role="admin"),
    "locked_user":   manager.create_test_user(status="locked"),
    "disabled_user": manager.create_test_user(status="disabled"),
}

# 落盘到权威路径（conftest test_data fixture 直接消费此文件）
out = Path("workspace/测试数据/test_data.json")
out.parent.mkdir(parents=True, exist_ok=True)
out.write_text(json.dumps(test_users, ensure_ascii=False, indent=2), encoding="utf-8")

# 日志中脱敏输出
logger.info(f"测试数据已生成: {DataMasker.mask_dict(test_users)}")
```

> 注：`_insert_to_db` / `_delete_from_db` 由 `utils/data_factory.py` 提供 SQLAlchemy 默认实现；项目可继承覆写。

### 步骤3：JMeter 参数化数据（性能场景）

```python
from jmeter_csv_exporter import generate_jmeter_dataset

# count 与 JMeter 并发数对齐
generate_jmeter_dataset(
    count=50,
    output_path="workspace/测试数据/jmeter_users.csv",
)
```

### 步骤4：数据验证

```python
def validate_test_data(test_data: dict) -> bool:
    """验证测试数据有效性（严格模式）"""
    required_keys = ["normal_user", "admin_user"]
    required_fields = ("user_id", "username", "password")

    failures = []
    for k in required_keys:
        if k not in test_data:
            failures.append(f"缺少 {k}")
            continue
        u = test_data[k]
        for f in required_fields:
            if not u.get(f):
                failures.append(f"{k}.{f} 为空")

    if failures:
        logger.error(f"❌ 数据验证失败: {failures}")
        return False
    logger.info("✅ 测试数据验证通过")
    return True
```

### 步骤5：清理钩子（双保险）

```python
import atexit

# atexit：进程正常退出时触发
atexit.register(manager.cleanup)

# pytest fixture：每个测试函数级 register_cleanup（已在 conftest.cleanup_tracker 提供）
```

## 📋 输出文件

| 文件 | 用途 | 消费方 |
|------|------|--------|
| `workspace/测试数据/test_data.json` | pytest 功能测试账号（conftest fixture 自动加载） | conftest / automation-engineer |
| `workspace/测试数据/jmeter_users.csv` | JMeter 参数化数据 | jmeter-script-gen / test-executor |
| `workspace/执行日志/数据准备报告_{日期}.json` | 数据准备详情 | test-lead |

## ⚠️ 数据安全要求

- 所有测试数据使用工厂生成（Faker），不使用真实用户数据
- 测试完成后必须清理：pytest fixture autouse + atexit 双保险
- 敏感字段（密码、手机号、邮箱、身份证、银行卡、token）日志输出前必须经 `DataMasker.mask_dict` 脱敏
- 数据创建失败时降级使用 `data_factory.LOGIN_TEST_DATA` 预设
