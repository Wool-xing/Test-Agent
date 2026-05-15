"""H2 hook 验证测试 · 故意含 ruff 违规 (unused import + bare except + line too long)."""

import os
import sys
import json  # unused, should trigger F401


def bad_func(x):
    try:
        return os.path.join(sys.argv[0], str(x)) + "_" + "really_really_really_long_string_to_trigger_line_length_warning_if_configured"
    except:  # noqa: E722 bare except, ruff E722
        pass
