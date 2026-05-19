"""把 InitAnswers + matrix + 模板 → 落盘 .env + tagent.yml + STARTUP.md."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from pathlib import Path

from runtime.init.matrix import Matrix, load_matrix
from runtime.init.wizard import InitAnswers


def _templates_dir() -> Path:
    from runtime.config.settings import get_settings

    return get_settings().project_root / "config" / "templates"


def _read_version() -> str:
    from runtime.config.settings import get_settings

    p = get_settings().project_root / "VERSION"
    return p.read_text(encoding="utf-8").strip() if p.exists() else "0.0.0"


def _env_kv(key: str, value: str) -> str:
    return f'{key}="{value}"' if any(c in value for c in " <>") else f"{key}={value}"


def _build_env_blocks(ans: InitAnswers, m: Matrix) -> dict[str, str]:
    t = m.test_types[ans.test_type]
    p = m.platforms[ans.platform]
    llm = m.llm_providers[ans.llm_provider]
    bt = m.bug_trackers[ans.bug_tracker]

    return {
        "LLM_ENV_BLOCK": "\n".join(_env_kv(k, v) for k, v in llm.env.items())
        + (f"\n# LLM model hint: {llm.model_hint}" if llm.model_hint else ""),
        "TEST_REQUIRED_ENV_BLOCK": "\n".join(_env_kv(k, "<填这里>") for k in t.required_env),
        "PLATFORM_EXTRAS_BLOCK": "\n".join(_env_kv(k, "<填这里>") for k in p.extras) or "# (无平台 extras)",
        "BUG_TRACKER_ENV_BLOCK": "\n".join(_env_kv(k, v) for k, v in bt.env.items()),
        "NOTIFIER_ENV_BLOCK": "\n".join(
            "\n".join(_env_kv(k, v) for k, v in m.notifiers[n].env.items()) for n in ans.notifiers
        )
        or "# (未启用任何通知渠道)",
    }


def _build_tpl_vars(ans: InitAnswers, m: Matrix) -> dict[str, str]:
    t = m.test_types[ans.test_type]
    p = m.platforms[ans.platform]
    bt = m.bug_trackers[ans.bug_tracker]

    notifier_labels = ", ".join(m.notifiers[n].label for n in ans.notifiers) or "(无)"
    notifier_yaml_list = "[" + ", ".join(ans.notifiers) + "]" if ans.notifiers else "[]"

    skills_yaml = "\n".join(f"    - {s}" for s in t.default_skills)
    skills_numbered = "\n".join(f"{i+1}. `{s}`" for i, s in enumerate(t.default_skills))

    required_fills = "\n".join(f"- `{k}` ({_required_hint(k, ans, m)})" for k in t.required_env)
    required_fills += "\n" + "\n".join(
        f"- `{k}` (BugTracker:{bt.label})" for k, v in bt.env.items() if v.startswith("<") and v.endswith(">")
    )
    for n in ans.notifiers:
        ne = m.notifiers[n]
        required_fills += "\n" + "\n".join(
            f"- `{k}` (通知:{ne.label})" for k, v in ne.env.items() if v.startswith("<") and v.endswith(">")
        )

    platform_deps_hint = {
        "linux": "# 大部分依赖 apt-get 已装",
        "windows": "# (Windows 用户:确保 python-docx 装 openpyxl 在 wheel 兜底)",
        "mac": "# brew install ...(按需)",
        "android": "playwright install chromium  # 桌面驱动 Appium 走 npm install -g appium",
        "ios": "# xcrun simctl + Appium XCUITest driver(macOS 必须)",
        "embedded": "# 串口工具:pip install pyserial;MQTT:pip install paho-mqtt",
    }.get(ans.platform, "")

    sample_target = ans.sample_target or {
        "web": "https://example.com",
        "api": "https://api.example.com/v1",
        "mobile": "/path/to/app.apk",
        "desktop": "C:/Program Files/YourApp/YourApp.exe",
        "iot": "/dev/ttyUSB0",
        "car": "carla://localhost:2000",
        "ai_model": "https://api.openai.com/v1/chat/completions",
        "security": "https://target.example.com",
    }.get(ans.test_type, "(填一个被测对象)")

    return {
        "TAGENT_VERSION": _read_version(),
        "GENERATED_AT": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
        "TEST_TYPE": ans.test_type,
        "TEST_TYPE_LABEL": t.label,
        "PLATFORM": ans.platform,
        "PLATFORM_LABEL": p.label,
        "LLM_PROVIDER": ans.llm_provider,
        "BUG_TRACKER": ans.bug_tracker,
        "NOTIFIER_LIST": notifier_labels,
        "NOTIFIER_LIST_YAML": notifier_yaml_list,
        "RECOMMENDED_SKILLS_LIST": skills_yaml,
        "RECOMMENDED_SKILLS_NUMBERED": skills_numbered,
        "REQUIRED_FILLS_BLOCK": required_fills,
        "PLATFORM_DEPS_HINT": platform_deps_hint,
        "SAMPLE_TARGET": sample_target,
    }


def _required_hint(key: str, ans: InitAnswers, m: Matrix) -> str:
    hints = {
        "TEST_APP_URL": "网页根 URL,如 https://example.com",
        "PYTEST_BROWSER": "chromium / firefox / webkit",
        "API_BASE_URL": "API base,如 https://api.example.com",
        "API_AUTH_TOKEN": "Bearer token 或 OAuth 配置",
        "APP_SRC_PATH": "APK / IPA 文件路径",
        "APPIUM_SERVER_URL": "默认 http://localhost:4723",
        "APP_EXE_PATH": "桌面 app 可执行文件路径",
        "DEVICE_SERIAL_PORT": "串口设备,如 /dev/ttyUSB0",
        "MQTT_BROKER_URL": "mqtt://broker:1883",
        "CAN_INTERFACE": "can0 / vcan0",
        "CARLA_SERVER_URL": "carla://localhost:2000",
        "MODEL_ENDPOINT": "LLM API 端点",
        "EVAL_DATASET_PATH": "评测集 JSONL 路径",
        "TARGET_URL": "渗透目标 URL",
        "SCAN_PROFILE": "quick / full / stealth",
    }
    return hints.get(key, "见 config/INDEX.md")


def _apply(tpl: str, vars_: dict[str, str]) -> str:
    out = tpl
    for k, v in vars_.items():
        out = out.replace("{{" + k + "}}", v)
    return out


@dataclass(slots=True)
class RenderResult:
    env_path: Path
    yml_path: Path
    startup_path: Path


def render_all(answers: InitAnswers, out_dir: Path, matrix: Matrix | None = None, overwrite: bool = False) -> RenderResult:
    m = matrix or load_matrix()
    out_dir = out_dir.resolve()
    out_dir.mkdir(parents=True, exist_ok=True)

    tpl_dir = _templates_dir()
    env_tpl = (tpl_dir / "base.env.tpl").read_text(encoding="utf-8")
    yml_tpl = (tpl_dir / "base.tagent.yml.tpl").read_text(encoding="utf-8")
    startup_tpl = (tpl_dir / "STARTUP.md.tpl").read_text(encoding="utf-8")

    tpl_vars = _build_tpl_vars(answers, m)
    env_blocks = _build_env_blocks(answers, m)
    tpl_vars.update(env_blocks)

    env_path = out_dir / ".env"
    yml_path = out_dir / "tagent.yml"
    startup_path = out_dir / "STARTUP.md"

    for p in (env_path, yml_path, startup_path):
        if p.exists() and not overwrite:
            raise FileExistsError(f"refusing to overwrite {p}; pass --overwrite to force")

    env_path.write_text(_apply(env_tpl, tpl_vars), encoding="utf-8")
    yml_path.write_text(_apply(yml_tpl, tpl_vars), encoding="utf-8")
    startup_path.write_text(_apply(startup_tpl, tpl_vars), encoding="utf-8")
    return RenderResult(env_path=env_path, yml_path=yml_path, startup_path=startup_path)
