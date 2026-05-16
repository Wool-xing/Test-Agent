"""FastAPI app."""

from __future__ import annotations

import tempfile
from pathlib import Path

from fastapi import BackgroundTasks, FastAPI, File, Form, HTTPException, UploadFile
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from loguru import logger

from runtime import __version__
from runtime.api.deps import Kernel
from runtime.api.models import CatalogResponse, RunCreateText, RunCreated, RunStatus as RunStatusModel
from runtime.api.parsers import parse_path, parse_text, parse_url

app = FastAPI(title="Test-Agent Runtime", version=__version__)
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)
_kernel = Kernel()
_run_results: dict[str, dict] = {}


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
async def run_file(file: UploadFile = File(...), extra: str = Form("")) -> RunCreated:
    suffix = Path(file.filename or "upload").suffix
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


def _run_in_background(run_id: str, decision) -> None:
    try:
        summary = _kernel.execute_sync(run_id, decision)
        _run_results[run_id] = summary
    except Exception as e:  # noqa: BLE001
        logger.error("background run failed: {}", e)
        _run_results[run_id] = {"error": str(e), "failed": 1, "succeeded": 0, "total": 0}
