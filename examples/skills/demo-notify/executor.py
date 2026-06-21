"""Demo Notify executor — send test notifications."""


def execute(params: dict, ctx) -> dict:
    channel = params.get("channel", "console")
    message = params.get("message", "Test notification from Test-Agent")

    # In a real skill, this would connect to Slack/Email/Webhook APIs.
    # This demo just simulates the notification and always succeeds.
    print(f"[{channel}] {message}")

    return {
        "status": "pass",
        "summary": f"Notification sent to {channel}",
        "details": {"channel": channel, "message_length": len(message)},
        "checks": [{"name": "Sent", "expected": True, "actual": True, "pass": True}],
        "error": None,
    }
