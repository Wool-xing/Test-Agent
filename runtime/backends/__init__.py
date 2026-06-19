"""7 execution backends.

local / docker / ssh / singularity / modal / daytona / vercel_sandbox.
Use `get_backend(name)` to obtain an adapter implementing BaseExecutionEnv.
"""

# 触发 7 个 backend 的 @register("xxx") 装饰器,填充 REGISTRY
# 不导入这些模块 → REGISTRY 永空 → get_backend("local") KeyError 启动崩 (W4-4 修)
from runtime.backends import (  # noqa: F401, E402
    daytona,
    docker,
    local,
    modal,
    singularity,
    ssh,
    vercel_sandbox,
)
from runtime.backends.base import REGISTRY, BaseExecutionEnv, get_backend, register  # noqa: F401
