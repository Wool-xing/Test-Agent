"""Test-Agent runtime layer.

AI router + Prefect orchestrator + FastAPI/CLI entry + flywheel storage.
Wraps 16 experts + 32 skills + 76 utils without modifying them.
"""

from pathlib import Path as __Path


def _load_dotenv() -> None:
    """Load project root .env → os.environ (idempotent, safe to call repeatedly)."""
    try:
        from dotenv import load_dotenv as _ld
    except ImportError:
        return
    dotenv_path = __Path(__file__).resolve().parents[1] / ".env"
    if dotenv_path.is_file():
        _ld(dotenv_path=dotenv_path, override=False)


_load_dotenv()


def _read_version() -> str:
    """从项目根 VERSION 文件读取版本号，单点 source of truth。"""
    vf = __Path(__file__).resolve().parents[1] / "VERSION"
    if vf.is_file():
        return vf.read_text(encoding="utf-8").strip().lstrip("Vv")
    return "0.0.0"


__version__ = _read_version()
