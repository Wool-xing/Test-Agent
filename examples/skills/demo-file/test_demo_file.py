"""Tests for demo-file skill."""

import tempfile
from pathlib import Path
from executor import execute


def test_file_exists():
    with tempfile.NamedTemporaryFile(delete=False, suffix=".txt") as f:
        f.write(b"hello world")
        path = f.name
    result = execute({"path": path}, None)
    assert result["status"] == "pass"
    Path(path).unlink()


def test_file_not_found():
    result = execute({"path": "/nonexistent/file.xyz"}, None)
    assert result["status"] == "fail"


def test_min_size():
    with tempfile.NamedTemporaryFile(delete=False, suffix=".txt") as f:
        f.write(b"hello world")
        path = f.name
    result = execute({"path": path, "min_size": 5}, None)
    assert result["status"] == "pass"
    result2 = execute({"path": path, "min_size": 99999}, None)
    assert result2["status"] == "fail"
    Path(path).unlink()
