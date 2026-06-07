"""Multi-platform messaging gateway · .

Single gateway process serves N platforms. Cross-platform conversation continuity.
"""

# 触发 8 个 platform 子模块 @register("xxx") 装饰器加载,填充 REGISTRY
# 不导入 platforms 包 → REGISTRY 永空 → get_platform("feishu") KeyError (W4-4 同模式扩散修)
from runtime.gateway import platforms  # noqa: F401, E402
from runtime.gateway.base import REGISTRY, Platform, get_platform, register  # noqa: F401
