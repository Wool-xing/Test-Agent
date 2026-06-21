"""Tests for demo-http skill."""

from executor import execute


def test_missing_url():
    result = execute({"url": ""}, None)
    assert result["status"] == "error"
    assert "url is required" in result["summary"]


def test_invalid_url():
    result = execute({"url": "not-a-url"}, None)
    assert result["status"] == "error"


def test_valid_url():
    result = execute({"url": "https://httpbin.org/get", "expected_status": 200}, None)
    assert result["status"] in ("pass", "error")  # error if offline
    assert "url" in result["details"]


def test_custom_timeout():
    result = execute({"url": "https://httpbin.org/get", "timeout": 5}, None)
    assert result["status"] in ("pass", "error")


def test_unreachable_host():
    result = execute({"url": "https://192.0.2.1", "timeout": 2}, None)
    assert result["status"] == "error"
    assert "Connection failed" in result["summary"]
