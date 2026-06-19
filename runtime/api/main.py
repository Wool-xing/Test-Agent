"""FastAPI app."""

from __future__ import annotations

import secrets
import tempfile
import threading
from pathlib import Path
from typing import Any

from fastapi import BackgroundTasks, FastAPI, File, Form, HTTPException, Request, UploadFile
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse as _JSONResponse
from loguru import logger

from runtime import __version__
from runtime.api.correlation import CorrelationMiddleware
from runtime.api.deps import Kernel
from runtime.api.endpoints.cancel import router as cancel_router
from runtime.api.endpoints.stream import router as stream_router
from runtime.api.endpoints.webhooks import router as webhooks_router
from runtime.api.marketplace_api import router as marketplace_router
from runtime.api.models import CatalogResponse, RunCreated, RunCreateText
from runtime.api.models import RunStatus as RunStatusModel
from runtime.api.parsers import parse_path, parse_text, parse_url
from runtime.api.result_store import ResultStore
from runtime.config.settings import get_settings
from runtime.observability.prometheus_metrics import create_metrics_router

import os as _os

_DEFAULT_UPLOAD_EXTS: set[str] = {
    ".md", ".txt", ".pdf", ".docx", ".xlsx", ".zip",
    ".png", ".jpg", ".jpeg", ".html", ".json", ".yml", ".yaml",
    ".py", ".js", ".ts", ".apk", ".ipa",
}


def _allowed_upload_exts() -> set[str]:
    custom = _os.getenv("TAGENT_ALLOWED_UPLOAD_EXTS")
    return set(custom.split(",")) if custom else _DEFAULT_UPLOAD_EXTS


class JSONResponse(_JSONResponse):
    """JSONResponse that writes raw UTF-8 bytes — CJK chars unescaped."""

    def render(self, content: Any) -> bytes:
        import json as _json

        return _json.dumps(
            content, ensure_ascii=False, allow_nan=False, separators=(",", ":")
        ).encode("utf-8")


_settings = get_settings()

app = FastAPI(title="Test-Agent Runtime", version=__version__, default_response_class=JSONResponse)
app.add_middleware(
    CORSMiddleware,
    allow_origins=["tauri://localhost"],
    allow_origin_regex=r"https?://(localhost|127\.0\.0\.1)(:\d+)?",
    allow_methods=["GET", "POST"],
    allow_headers=["Content-Type", "Authorization"],
)

app.add_middleware(CorrelationMiddleware)

# Prometheus metrics (zero-config)
_metrics_router = create_metrics_router()
if _metrics_router is not None:
    app.include_router(_metrics_router)
app.include_router(cancel_router)
app.include_router(stream_router)
app.include_router(webhooks_router)
app.include_router(marketplace_router)

# Bearer token auth middleware — enforced only when TAGENT_API_AUTH_TOKEN is set
@app.middleware("http")
async def auth_middleware(request: Request, call_next: Any) -> Any:
    token = _settings.api_auth_token
    _public_paths = ("/health", "/health/deep", "/docs", "/openapi.json")
    if token and not request.url.path.startswith("/api/marketplace") and request.url.path not in _public_paths:
        auth = request.headers.get("Authorization", "")
        if not auth or not secrets.compare_digest(auth.removeprefix("Bearer "), token):
            return JSONResponse(status_code=401, content={"detail": "unauthorized"})
    return await call_next(request)

_kernel = Kernel()
_run_results = ResultStore(max_entries=1000, ttl_seconds=86400)
_run_lock = threading.Lock()


@app.get("/health")
def health() -> dict:
    return {"status": "ok", "version": __version__}


@app.get("/health/deep")
def health_deep() -> dict:
    from runtime.cli.doctor import (
        check_catalog,
        check_config,
        check_dependencies,
        check_environment,
        check_llm,
        check_workspace,
    )

    sections: dict[str, list[dict]] = {}
    for name, fn in [
        ("environment", check_environment),
        ("catalog", check_catalog),
        ("config", check_config),
        ("dependencies", check_dependencies),
        ("llm", check_llm),
        ("workspace", check_workspace),
    ]:
        sections[name] = fn()

    all_ok = all(ch["ok"] for s in sections.values() for ch in s)
    return {"status": "ok" if all_ok else "degraded", "version": __version__, "checks": sections}


@app.get("/catalog", response_model=CatalogResponse)
def catalog() -> CatalogResponse:
    data = _kernel.catalog()
    return CatalogResponse(**data)


@app.post("/run/text", response_model=RunCreated)
def run_text(payload: RunCreateText, bg: BackgroundTasks, mode: str = "exec", lang: str = "zh") -> RunCreated:
    # mode+lang per-request
    from runtime.tutor.i18n import set_lang
    from runtime.tutor.verbosity import set_mode

    set_mode(mode)
    set_lang(lang)
    art = parse_text(payload.text)
    run_id, decision = _kernel.submit(art)
    bg.add_task(_run_in_background, run_id, decision)
    return RunCreated(
        run_id=run_id,
        decision_summary={
            "detected_target_type": decision.detected_target_type,
            "detected_qualities": decision.detected_qualities,
            "confidence": decision.confidence,
            "rationale": decision.rationale,
            "nodes": [{"id": n.id, "kind": n.kind, "name": n.name} for n in decision.dag],
        },
        accepted=True,
    )


@app.post("/run/file", response_model=RunCreated)
async def run_file(file: UploadFile = File(..., max_length=50_000_000), bg: BackgroundTasks = None, extra: str = Form("")) -> RunCreated:  # type: ignore[assignment]  # noqa: B008
    suffix = Path(file.filename or "upload").suffix.lower()
    allowed = _allowed_upload_exts()
    if suffix not in allowed:
        raise HTTPException(status_code=400, detail=f"file type not supported: {suffix}")
    with tempfile.NamedTemporaryFile(delete=False, suffix=suffix) as tmp:
        tmp.write(await file.read())
        tmp_path = Path(tmp.name)
    art = parse_path(tmp_path)
    if extra:
        art.text = (art.text or "") + "\n\n# User note:\n" + extra
    run_id, decision = _kernel.submit(art)
    bg.add_task(_run_in_background, run_id, decision)
    return RunCreated(
        run_id=run_id,
        decision_summary={
            "detected_target_type": decision.detected_target_type,
            "detected_qualities": decision.detected_qualities,
            "confidence": decision.confidence,
            "rationale": decision.rationale,
            "nodes": [{"id": n.id, "kind": n.kind, "name": n.name} for n in decision.dag],
        },
        accepted=True,
    )


@app.post("/run/url", response_model=RunCreated)
def run_url(url: str = Form(...), bg: BackgroundTasks = None) -> RunCreated:  # type: ignore[assignment]
    art = parse_url(url)
    run_id, decision = _kernel.submit(art)
    bg.add_task(_run_in_background, run_id, decision)
    return RunCreated(
        run_id=run_id,
        decision_summary={
            "detected_target_type": decision.detected_target_type,
            "confidence": decision.confidence,
            "nodes": [{"id": n.id, "kind": n.kind, "name": n.name} for n in decision.dag],
        },
        accepted=True,
    )


@app.get("/status/{run_id}", response_model=RunStatusModel)
def status(run_id: str) -> RunStatusModel:
    res = _run_results.get(run_id)
    if res is None:
        return RunStatusModel(run_id=run_id, status="running", total=0)
    status_str = "succeeded" if res.get("failed", 0) == 0 else "failed"
    return RunStatusModel(
        run_id=run_id,
        status=status_str,
        succeeded=res.get("succeeded", 0),
        failed=res.get("failed", 0),
        total=res.get("total", 0),
        detail=res,
    )


@app.get("/report/{run_id}")
def report(run_id: str) -> JSONResponse:
    res = _run_results.get(run_id)
    if res is None:
        raise HTTPException(status_code=404, detail="run not finished or unknown")
    return JSONResponse(res)


@app.post("/feedback")
def submit_feedback(payload: dict) -> dict:
    """Accept user feedback from desktop/web UI. Logs to workspace/feedback/."""
    import json as _json
    from datetime import datetime, timezone

    fb_dir = get_settings().workspace_dir / "feedback"
    fb_dir.mkdir(parents=True, exist_ok=True)
    entry = {
        **payload,
        "received_at": datetime.now(timezone.utc).isoformat(),
    }
    ts = datetime.now(timezone.utc).strftime("%Y%m%d-%H%M%S")
    fname = fb_dir / f"feedback-{ts}.json"
    fname.write_text(_json.dumps(entry, indent=2, ensure_ascii=False), encoding="utf-8")
    logger.info("feedback saved: {}", fname)
    return {"status": "ok", "saved_to": str(fname)}


@app.get("/history")
def list_history() -> dict:
    """List past test runs from workspace."""
    import json as _json

    ws = get_settings().workspace_dir
    runs: list[dict] = []

    # Scan workspace/_demo and workspace/测试报告 for run outputs
    for scan_dir in [ws / "_demo", ws / "测试报告"]:
        if not scan_dir.exists():
            continue
        for f in sorted(scan_dir.rglob("*.json"), reverse=True):
            try:
                data = _json.loads(f.read_text(encoding="utf-8"))
                if isinstance(data, dict) and "run_id" in data:
                    runs.append({
                        "run_id": data.get("run_id", f.stem),
                        "target": data.get("target", data.get("target_type", f.stem)),
                        "date": data.get("date", data.get("timestamp", "")),
                        "total": data.get("total", 0),
                        "passed": data.get("succeeded", data.get("passed", 0)),
                        "failed": data.get("failed", 0),
                        "duration_s": data.get("duration_s", data.get("duration_ms", 0) / 1000 if "duration_ms" in data else 0),
                        "confidence": data.get("confidence", 0),
                    })
            except (OSError, _json.JSONDecodeError, ValueError) as e:
                logger.warning("skipping unreadable run file {}: {}", f, e)

    return {"runs": runs[:50]}


@app.get("/dashboard")
def get_dashboard() -> dict:
    """Aggregate quality metrics — 3‑row layout: decision → diagnostic → action."""
    from runtime.observability.dashboard import build_dashboard

    ws = get_settings().workspace_dir
    return build_dashboard(ws)


def _run_in_background(run_id: str, decision) -> None:
    try:
        summary = _kernel.execute_sync(run_id, decision)
        with _run_lock:
            _run_results.put(run_id, summary)
    except Exception:  # noqa: BLE001
        logger.exception("background run {} failed", run_id)
        with _run_lock:
            _run_results.put(run_id, {
                "error": f"run {run_id} failed — check logs at workspace/ or run with --debug",
                "run_id": run_id,
                "failed": 1, "succeeded": 0, "total": 0, "status": "error",
            })
