# SPDX-License-Identifier: MIT
"""
数据库测试工具：CRUD / 事务 ACID / 迁移 / 备份恢复 / 慢查询 / 死锁
被引用方：05-数据准备 + 安全/可靠性测试

依赖：SQLAlchemy（已在 requirements）
"""
import json
import logging
import subprocess
import time
from contextlib import contextmanager
from pathlib import Path
from typing import Dict, List, Optional

logger = logging.getLogger(__name__)


# ===== 事务 ACID =====

@contextmanager
def transactional_test(engine):
    """
    每个测试包在事务中，结束自动 rollback（保数据库洁净）。
    用法：
        with transactional_test(engine) as conn:
            conn.execute(...)
    """
    conn = engine.connect()
    trans = conn.begin()
    try:
        yield conn
    finally:
        trans.rollback()
        conn.close()


def assert_atomicity(engine, ops_func):
    """
    原子性断言：ops_func 内一连串操作要么全成要么全失败。
    ops_func(conn) 会被调用，里面应包含 raise 触发回滚。
    """
    from sqlalchemy import text
    before = engine.connect().execute(text("SELECT count(*) FROM users")).scalar()
    try:
        with engine.begin() as conn:
            ops_func(conn)
    except Exception as e:
        logger.info(f"事务失败（预期）: {e}")
    after = engine.connect().execute(text("SELECT count(*) FROM users")).scalar()
    return {"before": before, "after": after, "atomicity_pass": before == after}


# ===== 死锁检测 =====

def detect_deadlock(engine, scenario_a, scenario_b, timeout: int = 10) -> Dict:
    """
    并发执行 scenario_a 和 scenario_b，检测死锁。
    scenario_a/b 是 callable(conn) 接受连接对象。
    """
    import threading
    results = {"a_error": None, "b_error": None, "deadlock_detected": False}

    def run(scenario, key):
        try:
            with engine.begin() as conn:
                scenario(conn)
        except Exception as e:
            results[key] = str(e)
            if "deadlock" in str(e).lower() or "lock wait" in str(e).lower():
                results["deadlock_detected"] = True

    t1 = threading.Thread(target=run, args=(scenario_a, "a_error"))
    t2 = threading.Thread(target=run, args=(scenario_b, "b_error"))
    t1.start(); t2.start()
    t1.join(timeout); t2.join(timeout)
    return results


# ===== 慢查询检测 =====

def explain_query(engine, sql: str) -> Dict:
    """EXPLAIN 查询执行计划"""
    from sqlalchemy import text
    with engine.connect() as conn:
        plan = conn.execute(text(f"EXPLAIN {sql}")).fetchall()
    return {"sql": sql, "plan": [str(r) for r in plan]}


def benchmark_query(engine, sql: str, iterations: int = 100) -> Dict:
    """查询性能 benchmark"""
    from sqlalchemy import text
    times = []
    with engine.connect() as conn:
        for _ in range(iterations):
            t0 = time.time()
            conn.execute(text(sql)).fetchall()
            times.append((time.time() - t0) * 1000)
    times.sort()
    return {
        "iterations": iterations,
        "avg_ms": round(sum(times) / len(times), 2),
        "p50_ms": round(times[int(iterations * 0.5)], 2),
        "p95_ms": round(times[int(iterations * 0.95)], 2),
        "max_ms": round(times[-1], 2),
    }


# ===== 数据迁移 up/down =====

def test_migration(alembic_cmd: str = "alembic", target: str = "head") -> Dict:
    """
    测试 Alembic 迁移：upgrade → downgrade → upgrade，保证幂等。
    """
    results = {}
    for action in ["upgrade head", "downgrade -1", "upgrade head"]:
        proc = subprocess.run(
            [alembic_cmd] + action.split(),
            capture_output=True, text=True, timeout=300,
        )
        results[action] = {
            "exit_code": proc.returncode,
            "stderr": proc.stderr[-500:] if proc.stderr else "",
        }
    return results


# ===== 备份 / 恢复演练 =====

def test_postgres_backup_restore(host: str, db: str, user: str, password: str,
                                   backup_file: str = "/tmp/backup.dump") -> Dict:
    """pg_dump + pg_restore 演练"""
    import os
    env = os.environ.copy()
    env["PGPASSWORD"] = password

    # 1. dump
    dump = subprocess.run(
        ["pg_dump", "-h", host, "-U", user, "-Fc", "-f", backup_file, db],
        env=env, capture_output=True, text=True, timeout=600,
    )
    if dump.returncode != 0:
        return {"backup": "fail", "error": dump.stderr}

    # 2. 恢复到临时库
    test_db = f"{db}_restore_test"
    subprocess.run(["psql", "-h", host, "-U", user, "-c", f"CREATE DATABASE {test_db}"],
                   env=env, capture_output=True)
    restore = subprocess.run(
        ["pg_restore", "-h", host, "-U", user, "-d", test_db, backup_file],
        env=env, capture_output=True, text=True, timeout=600,
    )
    subprocess.run(["psql", "-h", host, "-U", user, "-c", f"DROP DATABASE {test_db}"],
                   env=env, capture_output=True)

    return {
        "backup": "ok" if dump.returncode == 0 else "fail",
        "restore": "ok" if restore.returncode == 0 else "fail",
        "backup_file": backup_file,
    }


# ===== 主从延迟 =====

def check_replication_lag_postgres(master_engine, replica_engine) -> Dict:
    """PostgreSQL 主从同步延迟（秒）"""
    from sqlalchemy import text
    with master_engine.connect() as m, replica_engine.connect() as r:
        master_lsn = m.execute(text("SELECT pg_current_wal_lsn()")).scalar()
        r.execute(text("SELECT pg_last_wal_replay_lsn()"))
        lag = r.execute(text(
            "SELECT EXTRACT(EPOCH FROM (now() - pg_last_xact_replay_timestamp()))"
        )).scalar()
    return {"master_lsn": master_lsn, "replica_lag_sec": lag or 0}


if __name__ == "__main__":
    import argparse
    logging.basicConfig(level=logging.INFO)
    print("db_test_helper module loaded")
