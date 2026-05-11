"""7 execution backends · hermes §1.4.

local / docker / ssh / singularity / modal / daytona / vercel_sandbox.
Use `get_backend(name)` to obtain an adapter implementing BaseExecutionEnv.
"""

from runtime.backends.base import BaseExecutionEnv, REGISTRY, get_backend, register  # noqa: F401
