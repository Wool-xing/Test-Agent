"""Tests for demo-notify skill."""

from executor import execute


def test_default_channel():
    result = execute({}, None)
    assert result["status"] == "pass"
    assert result["details"]["channel"] == "console"


def test_custom_message():
    result = execute({"channel": "slack", "message": "Deploy complete"}, None)
    assert result["status"] == "pass"
    assert result["details"]["channel"] == "slack"
    assert result["details"]["message_length"] > 0
