"""specs.gates — Canonical quality gate definitions.

Each gate is a YAML file in this directory. The GateRegistry loads
all gates at import time and provides lookup, listing, and evaluation.
"""

from __future__ import annotations

from specs.gates.registry import Gate, GateCheck, GateRegistry

__all__ = ["Gate", "GateCheck", "GateRegistry"]
