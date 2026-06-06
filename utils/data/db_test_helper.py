# SPDX-License-Identifier: MIT
"""
数据库测试工具：CRUD / 事务 ACID / 迁移 / 备份恢复 / 慢查询 / 死锁
被引用方：05-数据准备 + 安全/可靠性测试

依赖：SQLAlchemy（已在 requirements）

安全约束（W5-3 加固）：
    本模块多个函数执行未参数化的 SQL / shell 子进程 / CREATE/DROP DATABASE，
    设计上接受"调用方信任 SQL 输入"。为防止误用：
      - 高风险操作（explain_query / benchmark_query / test_postgres_backup_restore /
        test_migration）需要环境变量 TAGENT_DB_TEST_AUTHORIZED=1 显式授权。
      - test_postgres_backup_restore 额外要求 confirm_destructive=True kwarg。
      - 数据库名 / 命令名经正则白名单校验。
    授权 ONLY 在专用测试数据库 / 隔离环境。生产库严禁。
"""
import json
import logging
import os
import re
import subprocess
import time
from contextlib import contextmanager
from pathlib import Path
from typing import Dict, List, Optional

logger = logging.getLogger(__name__)


# ===== W5-3 安全 gate =====

_GATE_ENV_VAR = "TAGENT_DB_TEST_AUTHORIZED"
_IDENT_RE = re.compile(r"^[A-Za-z_][A-Za-z0-9_]{0,62}$")
_CMD_RE = re.compile(r"^[A-Za-z0-9_./\-]+$")


def _gate_enabled() -> bool:
    return os.getenv(_GATE_ENV_VAR) == "1"


def _require_authorized(op: str) -> None:
    """高风险 DB 测试操作准入守卫。"""
    if not _gate_enabled():
        raise RuntimeError(
            f"db_test op '{op}' refused: set {_GATE_ENV_VAR}=1 to enable. "
            "Authorize ONLY in dedicated test databases / isolated environments. "
            "Risks: raw SQL execution, CREATE/DROP DATABASE, schema mutation, "
            "subprocess invocation."
        )


def _validate_identifier(name: str, kind: str = "identifier") -> str:
    """SQL identifier 白名单校验（用于无法参数化的位置，如 CREATE DATABASE）。"""
    if not isinstance(name, str) or not _IDENT_RE.fullmatch(name):
        raise ValueError(
            f"invalid {kind}: {name!r}. allowed pattern: "
            f"^[A-Za-z_][A-Za-z0-9_]{{0,62}}$ (letters/digits/underscore, "
            "must not start with digit, max 63 chars)"
        )
    return name


def _validate_command(cmd: str) -> str:
    """子进程命令名白名单校验。"""
    if not isinstance(cmd, str) or not _CMD_RE.fullmatch(cmd):
        raise ValueError(
            f"invalid command: {cmd!r}. allowed pattern: ^[A-Za-z0-9_./\\-]+$"
        )
    return cmd


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
    """EXPLAIN 查询执行计划。

    安全：sql 直接拼到 EXPLAIN 后执行，调用方必须保证 sql 为受信内容
    （不接受用户输入）。需 TAGENT_DB_TEST_AUTHORIZED=1。
    """
    _require_authorized("explain_query")
    from sqlalchemy import text
    with engine.connect() as conn:
        plan = conn.execute(text(f"EXPLAIN {sql}")).fetchall()
    return {"sql": sql, "plan": [str(r) for r in plan]}


def benchmark_query(engine, sql: str, iterations: int = 100) -> Dict:
    """查询性能 benchmark。

    安全：执行任意 sql 共 iterations 次，调用方必须保证 sql 为受信内容
    （不接受用户输入）。需 TAGENT_DB_TEST_AUTHORIZED=1。
    """
    _require_authorized("benchmark_query")
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

    安全：调用 subprocess 执行 alembic_cmd，需 TAGENT_DB_TEST_AUTHORIZED=1，
    且 alembic_cmd 经命令白名单校验。
    """
    _require_authorized("test_migration")
    _validate_command(alembic_cmd)
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
                                   backup_file: str = "/tmp/backup.dump",
                                   *,
                                   confirm_destructive: bool = False) -> Dict:
    """pg_dump + pg_restore 演练。

    安全：
      - 需 TAGENT_DB_TEST_AUTHORIZED=1（env gate）。
      - 需 confirm_destructive=True（kwarg opt-in，防误调）。
      - db 经 identifier 白名单校验（CREATE/DROP DATABASE 无法参数化）。
      - 临时库 DROP 在 try/finally 中，restore 异常也会清理。
    """
    _require_authorized("test_postgres_backup_restore")
    if not confirm_destructive:
        raise RuntimeError(
            "test_postgres_backup_restore refused: pass confirm_destructive=True "
            "to acknowledge that this will CREATE/DROP a database named "
            f"'{db}_restore_test' on host '{host}'."
        )
    _validate_identifier(db, "database name")

    env = os.environ.copy()
    env["PGPASSWORD"] = password

    # 1. dump
    dump = subprocess.run(
        ["pg_dump", "-h", host, "-U", user, "-Fc", "-f", backup_file, db],
        env=env, capture_output=True, text=True, timeout=600,
    )
    if dump.returncode != 0:
        return {"backup": "fail", "error": dump.stderr}

    # 2. 恢复到临时库（identifier 白名单校验后拼接安全）
    test_db = f"{db}_restore_test"
    _validate_identifier(test_db, "restore test database name")
    subprocess.run(["psql", "-h", host, "-U", user, "-c", f"CREATE DATABASE {test_db}"],
                   env=env, capture_output=True)
    try:
        restore = subprocess.run(
            ["pg_restore", "-h", host, "-U", user, "-d", test_db, backup_file],
            env=env, capture_output=True, text=True, timeout=600,
        )
    finally:
        # 即使 restore 抛异常或被信号打断也要清理临时库
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
