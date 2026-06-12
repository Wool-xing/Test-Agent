"""Pydantic models for router decision + DAG."""

from __future__ import annotations

from typing import Literal

from pydantic import BaseModel, Field, field_validator, model_validator

NodeKind = Literal["expert", "skill", "script"]


class DAGNode(BaseModel):
    id: str = Field(description="unique node id within DAG")
    kind: NodeKind
    name: str = Field(description="expert name / skill name / script filename")
    depends_on: list[str] = Field(default_factory=list)
    dep_mode: Literal["hard", "soft"] = "hard"
    inputs: dict[str, object] = Field(default_factory=dict)
    on_failure: Literal["retry", "skip", "abort"] = "retry"
    timeout_seconds: int = Field(default=1800, ge=1, description="node timeout in seconds")

    # Charter 教学层字段(可选;LLM 在 learn mode 应填,exec mode 仅 one_liner)
    one_liner_zh: str = Field(default="", description="≤30 字 why,执行模式输出此字段")
    one_liner_en: str = Field(default="", description="≤120 chars why for English")
    why: str = Field(default="", description="long-form rationale (learn mode)")
    theory_refs: list[str] = Field(default_factory=list, description="KB card ids (must exist in docs/theory)")
    alternatives: list[dict[str, str]] = Field(default_factory=list, description="rejected options + reasons")

    @field_validator("id", "name")
    @classmethod
    def _nonempty(cls, v: str) -> str:
        if not v or not v.strip():
            raise ValueError("must be non-empty")
        return v.strip()


class RoutingDecision(BaseModel):
    """LLM output. Wraps DAG + diagnostic metadata."""

    dag: list[DAGNode]
    rationale: str = Field(description="why this combination, in <= 3 sentences")
    confidence: float = Field(ge=0.0, le=1.0)
    detected_target_type: str = Field(
        description="e.g. 'web-system', 'rest-api', 'mobile-app', 'desktop-app', 'docker-image', 'ai-model'"
    )
    detected_qualities: list[str] = Field(
        default_factory=list,
        description="quality attributes the test should cover (functional/perf/security/...)",
    )
    missing_inputs: list[str] = Field(
        default_factory=list,
        description="inputs the user did not provide; UI should prompt",
    )

    @model_validator(mode="after")
    def _check_duplicate_ids(self):
        ids=[n.id for n in self.dag]
        dups={i for i in ids if ids.count(i)>1}
        if dups:
            raise ValueError(f"Duplicate DAG node IDs: {dups}")
        return self

    def topological(self) -> list[DAGNode]:
        """Kahn's algorithm. Raises on cycle."""
        in_deg = {n.id: 0 for n in self.dag}
        adj: dict[str, list[str]] = {n.id: [] for n in self.dag}
        for n in self.dag:
            for d in n.depends_on:
                if d not in in_deg:
                    raise ValueError(f"unknown dep {d} for {n.id}")
                in_deg[n.id] += 1
                adj[d].append(n.id)
        ready = [nid for nid, deg in in_deg.items() if deg == 0]
        order: list[str] = []
        while ready:
            cur = ready.pop(0)
            order.append(cur)
            for nxt in adj[cur]:
                in_deg[nxt] -= 1
                if in_deg[nxt] == 0:
                    ready.append(nxt)
        if len(order) != len(self.dag):
            raise ValueError("DAG has cycles")
        idx = {n.id: n for n in self.dag}
        return [idx[i] for i in order]


class TargetArtifact(BaseModel):
    """Normalized input description fed to LLM."""

    kind: str = Field(description="'file' | 'directory' | 'text' | 'url'")
    path: str | None = None
    text: str | None = None
    mime: str | None = None
    size_bytes: int | None = None
    extra: dict[str, object] = Field(default_factory=dict)
