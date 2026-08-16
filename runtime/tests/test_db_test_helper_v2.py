"""Tests for utils/data/db_test_helper_v2.py integrity helpers.

Locks the rule: a DB error (down / wrong table / wrong column) must NEVER
read as "constraint enforced" — only sqlalchemy IntegrityError counts.
"""

from __future__ import annotations

import sqlite3
import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).parent.parent.parent))

import utils.data.db_test_helper_v2 as helper  # noqa: E402


@pytest.fixture(autouse=True)
def _authorize(monkeypatch):
    """Bypass the TAGENT_DB_TEST_AUTHORIZED=1 gate for these tests."""
    monkeypatch.setattr(helper, "AUTHORIZED", True)


class TestUniqueConstraint:
    def test_duplicate_rejected_counts_as_enforced(self, tmp_path):
        """Real sqlite table with UNIQUE column: second insert must fail."""
        db = tmp_path / "uniq.db"
        con = sqlite3.connect(db)
        con.execute("CREATE TABLE t (col TEXT UNIQUE)")
        con.commit()
        con.close()

        res = helper.test_unique_constraint(f"sqlite:///{db}", "t", "col", value="dup")
        assert res["passed"] is True

    def test_db_error_is_not_enforced(self, tmp_path):
        """Insert into a nonexistent table raises loudly, never returns 'enforced'."""
        db = tmp_path / "empty.db"
        con = sqlite3.connect(db)
        con.close()

        from sqlalchemy.exc import SQLAlchemyError

        with pytest.raises(SQLAlchemyError):
            helper.test_unique_constraint(f"sqlite:///{db}", "missing_table", "col")


class TestCheckConstraint:
    def test_invalid_value_rejected_counts_as_enforced(self, tmp_path):
        """Real sqlite table with CHECK: invalid value must fail."""
        db = tmp_path / "check.db"
        con = sqlite3.connect(db)
        con.execute("CREATE TABLE t (col INTEGER CHECK (col > 0))")
        con.commit()
        con.close()

        res = helper.test_check_constraint(f"sqlite:///{db}", "t", "col", 1, -1)
        assert res["passed"] is True

    def test_db_error_is_not_enforced(self, tmp_path):
        """Nonexistent table must not read as 'CHECK constraint enforced'."""
        db = tmp_path / "empty2.db"
        con = sqlite3.connect(db)
        con.close()

        res = helper.test_check_constraint(f"sqlite:///{db}", "missing_table", "col", 1, -1)
        assert res["passed"] is False
        assert "not a constraint violation" in res.get("error", "")


class TestForeignKeyIntegrity:
    def test_db_error_is_not_enforced(self, tmp_path):
        """Nonexistent table must not read as 'FK constraint enforced'."""
        db = tmp_path / "empty3.db"
        con = sqlite3.connect(db)
        con.close()

        res = helper.test_foreign_key_integrity(f"sqlite:///{db}", "missing_table", "col")
        assert res["passed"] is False
        assert "not a constraint violation" in res.get("error", "")
