"""Centralized permission engine — global (role-based) primitives.

Resource-scoped policies (project membership, task access) live next to their
modules (``app.modules.projects.permissions``, ``app.modules.tasks.dependencies``)
but are built from the same pattern: callable dependency classes that FastAPI
resolves per-request, raising :class:`ForbiddenError` on failure.
"""

from __future__ import annotations

from typing import Annotated

from fastapi import Depends

from app.core.exceptions import ForbiddenError
from app.modules.auth.dependencies import get_current_user
from app.modules.users.models import User
from app.shared.enums import UserRole


class RequireRole:
    """Route dependency enforcing a global role.

    Usage::

        @router.get("/", dependencies=[Depends(require_admin)])
    """

    def __init__(self, *roles: UserRole, detail: str = "Admin access required") -> None:
        self.roles = roles
        self.detail = detail

    async def __call__(self, user: Annotated[User, Depends(get_current_user)]) -> User:
        if user.role not in self.roles:
            raise ForbiddenError(self.detail)
        return user


require_admin = RequireRole(UserRole.admin)
