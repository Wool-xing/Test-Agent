"""FastAPI app."""

from __future__ import annotations

import tempfile
import threading
from pathlib import Path
from typing import Any

from fastapi import BackgroundTasks, FastAPI, File, Form, HTTPException, Request, UploadFile
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from loguru import logger

from runtime import __version__
from runtime.api.deps import Kernel
from runtime.api.models import CatalogResponse, RunCreateText, RunCreated, RunStatus as RunStatusModel
from runtime.api.parsers import parse_path, parse_text, parse_url
from runtime.config.settings import get_settings
from runtime.observability.prometheus_metrics import create_metrics_router
from runtime.api.correlation import CorrelationMiddleware
from runtime.api.endpoints.cancel import router as cancel_router, register_run, unregister_run
from runtime.api.endpoints.stream import router as stream_router
from runtime.api.result_store import ResultStore

_settings = get_settings()

app = FastAPI(title="Test-Agent Runtime", version=__version__)
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:*", "http://127.0.0.1:*", "tauri://localhost"],
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

# Bearer token auth middleware — enforced only when TAGENT_API_AUTH_TOKEN is set
@app.middleware("http")
async def auth_middleware(request: Request, call_next: Any) -> Any:
    token = _settings.api_auth_token
    if token and request.url.path not in ("/health", "/docs", "/openapi.json"):
        auth = request.headers.get("Authorization", "")
        if not auth or auth.removeprefix("Bearer ") != token:
            return JSONResponse(status_code=401, content={"detail": "unauthorized"})
    return await call_next(request)

_kernel = Kernel()
_run_results = ResultStore(max_entries=1000, ttl_seconds=86400)
_run_lock = threading.Lock()


@app.get("/health")
def health() -> dict:
    return {"status": "ok", "version": __version__}


@app.get("/catalog", response_model=CatalogResponse)
def catalog() -> CatalogResponse:
    data = _kernel.catalog()
    return CatalogResponse(**data)


@app.post("/run/text", response_model=RunCreated)
def run_text(payload: RunCreateText, bg: BackgroundTasks, mode: str = "exec", lang: str = "zh") -> RunCreated:
    # Charter §23 mode+lang per-request
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
async def run_file(file: UploadFile = File(..., max_length=50_000_000), extra: str = Form("")) -> RunCreated:
    suffix = Path(file.filename or "upload").suffix.lower()
    allowed = {".md", ".txt", ".pdf", ".docx", ".xlsx", ".zip", ".png", ".jpg", ".jpeg", ".html", ".json", ".yml", ".yaml", ".py", ".js", ".ts", ".apk", ".ipa"}
    if suffix not in allowed:
        raise HTTPException(status_code=400, detail=f"file type not supported: {suffix}")
    with tempfile.NamedTemporaryFile(delete=False, suffix=suffix) as tmp:
        tmp.write(await file.read())
        tmp_path = Path(tmp.name)
    art = parse_path(tmp_path)
    if extra:
        art.text = (art.text or "") + "\n\n# User note:\n" + extra
    run_id, decision = _kernel.submit(art)
    # Kick off in same process pool; fire-and-forget for v1 simplicity.
    import threading

    threading.Thread(target=_run_in_background, args=(run_id, decision), daemon=True).start()
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

    # Scan workspace/_demo and workspace/执行日志 for run outputs
    for scan_dir in [ws / "_demo", ws / "执行日志"]:
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
            except (OSError, json.JSONDecodeError, ValueError) as e:
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
            _run_results[run_id] = summary
    except Exception:  # noqa: BLE001
        logger.exception("background run {} failed", run_id)
        with _run_lock:
            _run_results[run_id] = {
                "error": f"run {run_id} failed — check logs at workspace/ or run with --debug",
                "run_id": run_id,
                "failed": 1, "succeeded": 0, "total": 0, "status": "error",
            }
