"""Permission application-facing services.

The package-level surface intentionally stays small. Internal modules such as
cache, repository, gateway, policy, and context helpers are implementation
details unless a caller has a direct need for them.
"""

from .service import PermissionContext, PermissionService, permission_service

__all__ = [
    "PermissionContext",
    "PermissionService",
    "permission_service",
]
