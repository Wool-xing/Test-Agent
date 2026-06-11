# SPDX-License-Identifier: MIT
# DEPRECATED: use data_factory_v2 instead. This file will be removed in V1.2.
"""
测试数据工厂 - Faker + Factory Boy 生成标准化测试数据
被引用方：05-数据准备 agent / data-preparation skill / conftest.py
"""
import os
import logging
from datetime import datetime
from typing import Any, Dict, List, Optional

import factory
from faker import Faker

logger = logging.getLogger(__name__)
fake = Faker("zh_CN")


# ===== 数据工厂 =====

class UserFactory(factory.Factory):
    class Meta:
        model = dict

    user_id = factory.LazyFunction(lambda: fake.uuid4())
    username = factory.LazyFunction(lambda: fake.user_name())
    email = factory.LazyFunction(lambda: fake.email())
    phone = factory.LazyFunction(lambda: fake.phone_number())
    real_name = factory.LazyFunction(lambda: fake.name())
    password = factory.LazyFunction(lambda: fake.password(length=12))
    role = "user"
    status = "active"
    created_at = factory.LazyFunction(lambda: datetime.now().isoformat())


class OrderFactory(factory.Factory):
    class Meta:
        model = dict

    order_id = factory.LazyFunction(lambda: f"ORD{fake.numerify('########')}")
    user_id = factory.LazyFunction(lambda: fake.uuid4())
    amount = factory.LazyFunction(
        lambda: round(fake.pyfloat(min_value=0.01, max_value=9999.99), 2)
    )
    status = factory.LazyAttribute(
        lambda _: fake.random_element(["pending", "paid", "shipped", "completed"])
    )
    created_at = factory.LazyFunction(lambda: datetime.now().isoformat())


# ===== 数据管理器 =====

class TestDataManager:
    """
    测试数据生命周期管理：创建/记录/清理。
    数据库写入默认用 SQLAlchemy；项目可在子类覆盖 _insert_to_db / _delete_from_db。
    """

    def __init__(self, env_config=None):
        self.config = env_config
        self.created_ids: List[tuple] = []  # [(table, id), ...]
        self._cleanup_tasks: List[tuple] = []  # 任意清理函数
        self._engine = None

    # ---- DB 连接 ----

    def _get_engine(self):
        if self._engine is not None:
            return self._engine
        try:
            from sqlalchemy import create_engine
        except ImportError:
            logger.warning("SQLAlchemy 未安装，跳过 DB 写入（仅返回内存数据）")
            return None
        if not self.config:
            return None
        url = (
            f"postgresql+psycopg2://{self.config.db_user}:{self.config.db_password}"
            f"@{self.config.db_host}:{self.config.db_port}/{self.config.db_name}"
        )
        self._engine = create_engine(url, pool_pre_ping=True)
        return self._engine

    def _insert_to_db(self, table: str, data: Dict) -> Optional[str]:
        """子类可覆盖。默认尝试 SQLAlchemy 通用插入。"""
        engine = self._get_engine()
        if engine is None:
            return data.get("user_id") or data.get("order_id")
        try:
            from sqlalchemy import MetaData, Table, insert
            meta = MetaData()
            tbl = Table(table, meta, autoload_with=engine)
            with engine.begin() as conn:
                result = conn.execute(insert(tbl).values(**data))
                pk = result.inserted_primary_key[0] if result.inserted_primary_key else None
                return str(pk) if pk else data.get("user_id")
        except Exception as e:
            logger.error(f"DB 插入失败 {table}: {e}")
            return None

    def _delete_from_db(self, table: str, record_id: str):
        engine = self._get_engine()
        if engine is None:
            return
        try:
            from sqlalchemy import MetaData, Table, delete
            meta = MetaData()
            tbl = Table(table, meta, autoload_with=engine)
            pk_col = list(tbl.primary_key.columns)[0]
            with engine.begin() as conn:
                conn.execute(delete(tbl).where(pk_col == record_id))
        except Exception as e:
            logger.warning(f"DB 删除失败 {table}.{record_id}: {e}")

    # ---- 公开 API ----

    def create_test_user(self, **overrides) -> Dict[str, Any]:
        user = UserFactory(**overrides)
        rid = self._insert_to_db("users", user) or user["user_id"]
        self.created_ids.append(("users", rid))
        return user

    def create_batch_users(self, count: int = 10, **overrides) -> List[Dict]:
        return [self.create_test_user(**overrides) for _ in range(count)]

    def create_test_order(self, **overrides) -> Dict[str, Any]:
        order = OrderFactory(**overrides)
        rid = self._insert_to_db("orders", order) or order["order_id"]
        self.created_ids.append(("orders", rid))
        return order

    def create_boundary_data(self, field_type: str) -> List[Any]:
        """
        生成边界值。每项标注 expected_valid（True=应被接受/False=应被拒绝）。
        """
        boundaries = {
            "string": [
                {"value": "", "expected_valid": False},
                {"value": "a", "expected_valid": True},
                {"value": "a" * 255, "expected_valid": True},
                {"value": "a" * 256, "expected_valid": False},
                {"value": "特殊字符!@#$%", "expected_valid": True},
                {"value": None, "expected_valid": False},
            ],
            "integer": [
                {"value": 0, "expected_valid": True},
                {"value": 1, "expected_valid": True},
                {"value": -1, "expected_valid": False},
                {"value": 2147483647, "expected_valid": True},
                {"value": 2147483648, "expected_valid": False},
            ],
            "email": [
                {"value": "valid@example.com", "expected_valid": True},
                {"value": "invalid-email", "expected_valid": False},
                {"value": "@example.com", "expected_valid": False},
                {"value": "user@", "expected_valid": False},
            ],
            "phone": [
                {"value": "13800138000", "expected_valid": True},
                {"value": "1380013800", "expected_valid": False},
                {"value": "138001380001", "expected_valid": False},
                {"value": "+8613800138000", "expected_valid": True},
            ],
        }
        return boundaries.get(field_type, [])

    # ---- 清理 ----

    def register_cleanup(self, func, *args, **kwargs):
        self._cleanup_tasks.append((func, args, kwargs))

    def cleanup(self):
        count = len(self.created_ids)
        for table, record_id in reversed(self.created_ids):
            try:
                self._delete_from_db(table, record_id)
            except Exception as e:
                logger.warning(f"清理失败 {table}.{record_id}: {e}")
        for func, args, kwargs in reversed(self._cleanup_tasks):
            try:
                func(*args, **kwargs)
            except Exception as e:
                logger.warning(f"清理任务失败: {e}")
        self.created_ids.clear()
        self._cleanup_tasks.clear()
        logger.info(f"测试数据清理完成，共清理 {count} 条记录")


# ===== 预设登录测试数据集 =====

LOGIN_TEST_DATA = {
    "valid_credentials": [
        {"username": "test_user_001", "password": "Test@123456", "expected": "success"},
        {"username": "test_admin", "password": "Admin@123456", "expected": "success"},
    ],
    "invalid_credentials": [
        {"username": "nonexistent", "password": "Test@123456", "expected": "user_not_found"},
        {"username": "test_user_001", "password": "WrongPass", "expected": "wrong_password"},
        {"username": "", "password": "Test@123456", "expected": "empty_username"},
        {"username": "test_user_001", "password": "", "expected": "empty_password"},
    ],
    "boundary_cases": [
        {"username": "a", "password": "Test@123456", "expected": "invalid_username"},
        {"username": "a" * 50, "password": "Test@123456", "expected": "username_too_long"},
        {"username": "test_user_001", "password": "12345", "expected": "password_too_short"},
    ],
    "security_cases": [
        {"username": "' OR '1'='1", "password": "anything", "expected": "sql_injection_blocked"},
        {"username": "<script>alert(1)</script>", "password": "Test@123456", "expected": "xss_blocked"},
    ],
}


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    mgr = TestDataManager()
    user = UserFactory()
    print(f"示例用户: {user}")
    order = OrderFactory()
    print(f"示例订单: {order}")
