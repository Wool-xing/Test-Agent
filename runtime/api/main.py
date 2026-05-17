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

_settings = get_settings()

app = FastAPI(title="Test-Agent Runtime", version=__version__)
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:*", "http://127.0.0.1:*", "tauri://localhost"],
    allow_methods=["GET", "POST"],
    allow_headers=["Content-Type", "Authorization"],
)

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
_run_results: dict[str, dict] = {}
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
    """Aggregate quality metrics from all runs."""
    import json as _json

    ws = get_settings().workspace_dir
    all_runs: list[dict] = []
    expert_fails: dict[str, int] = {}

    for scan_dir in [ws / "_demo", ws / "执行日志"]:
        if not scan_dir.exists():
            continue
        for f in scan_dir.rglob("*.json"):
            try:
                data = _json.loads(f.read_text(encoding="utf-8"))
                if isinstance(data, dict) and "total" in data:
                    all_runs.append(data)
                if "results" in data and isinstance(data["results"], dict):
                    for node_id, r in data["results"].items():
                        if not r.get("ok") and r.get("name"):
                            name = r["name"]
                            expert_fails[name] = expert_fails.get(name, 0) + 1
            except (OSError, json.JSONDecodeError, ValueError) as e:
                logger.warning("dashboard: skipping unreadable run file {}: {}", f, e)

    total = len(all_runs)
    if total == 0:
        return {
            "total_runs": 0, "avg_pass_rate": 0, "avg_confidence": 0,
            "total_test_cases": 0, "recent_runs": [], "top_failures": [],
        }

    pass_rates = [(r.get("succeeded", r.get("passed", 0)) / max(r.get("total", 1), 1)) for r in all_runs]
    confidences = [r.get("confidence", 0) for r in all_runs if isinstance(r.get("confidence"), (int, float))]
    total_cases = sum(r.get("total", 0) for r in all_runs)

    top = sorted(expert_fails.items(), key=lambda x: -x[1])[:10]

    recent = sorted(all_runs, key=lambda r: str(r.get("date", r.get("timestamp", ""))), reverse=True)[:10]
    recent_summaries = [
        {
            "run_id": r.get("run_id", ""),
            "target": r.get("target", r.get("target_type", "")),
            "date": str(r.get("date", r.get("timestamp", ""))),
            "total": r.get("total", 0),
            "passed": r.get("succeeded", r.get("passed", 0)),
            "failed": r.get("failed", 0),
            "confidence": r.get("confidence", 0),
            "duration_s": r.get("duration_s", 0),
        }
        for r in recent
    ]

    return {
        "total_runs": total,
        "avg_pass_rate": sum(pass_rates) / total,
        "avg_confidence": sum(confidences) / len(confidences) if confidences else 0,
        "total_test_cases": total_cases,
        "recent_runs": recent_summaries,
        "top_failures": [{"expert": name, "fail_count": cnt} for name, cnt in top],
    }


def _run_in_background(run_id: str, decision) -> None:
    try:
        summary = _kernel.execute_sync(run_id, decision)
        with _run_lock:
            _run_results[run_id] = summary
    except Exception:  # noqa: BLE001
        logger.exception("background run {} failed", run_id)
        with _run_lock:
            _run_results[run_id] = {"error": "internal error — see logs", "failed": 1, "succeeded": 0, "total": 0, "status": "error"}
