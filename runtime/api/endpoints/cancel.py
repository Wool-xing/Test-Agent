"""POST /run/{run_id}/cancel — cancel an in-progress test run."""

from __future__ import annotations

from fastapi import APIRouter, HTTPException

router = APIRouter(tags=["runs"])

# Shared cancel registry — populated by main.py at startup
_cancel_registry: dict[str, bool] = {}


def get_cancel_registry() -> dict[str, bool]:
    return _cancel_registry


def request_cancel(run_id: str) -> bool:
    """Set cancel flag for a run. Returns True if run was found."""
    if run_id in _cancel_registry:
        _cancel_registry[run_id] = True
        return True
    return False


def is_cancelled(run_id: str) -> bool:
    return _cancel_registry.get(run_id, False)


def register_run(run_id: str) -> None:
    _cancel_registry[run_id] = False


def unregister_run(run_id: str) -> None:
    _cancel_registry.pop(run_id, None)


@router.post("/run/{run_id}/cancel")
async def cancel_run(run_id: str):
    """Request cancellation of a running test."""
    if not request_cancel(run_id):
        raise HTTPException(status_code=404, detail=f"run '{run_id}' not found or already completed")
    return {"run_id": run_id, "status": "cancelling"}
