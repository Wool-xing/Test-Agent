"""Pydantic request/response models for the API."""

from __future__ import annotations

from typing import Literal

from pydantic import BaseModel, Field


class RunCreateText(BaseModel):
    """Create a run from a text prompt (no file upload)."""

    text: str = Field(min_length=1)
    extra: dict[str, str] = Field(default_factory=dict)


class RunCreated(BaseModel):
    run_id: str
    decision_summary: dict
    accepted: bool


class RunStatus(BaseModel):
    run_id: str
    status: Literal["pending", "running", "succeeded", "failed", "cancelled"]
    succeeded: int = 0
    failed: int = 0
    total: int = 0
    detail: dict | None = None


class CatalogResponse(BaseModel):
    experts: list[dict]
    skills: list[dict]
    counts: dict[str, int]
