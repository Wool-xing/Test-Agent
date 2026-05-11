"""Multi-platform messaging gateway · hermes §1.5.

Single gateway process serves N platforms. Cross-platform conversation continuity.
"""

from runtime.gateway.base import REGISTRY, Platform, register  # noqa: F401
