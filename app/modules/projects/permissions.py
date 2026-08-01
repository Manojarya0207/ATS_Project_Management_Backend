"""Project-scoped permission policies.

``ProjectAccessPolicy`` is a dependency class whose ``project_id`` parameter is
resolved from the route's path by name. It loads the project once (404 when
missing) and enforces access (admins always pass; otherwise the user must be a
member, optionally with a minimum project role) — routes and services never
re-implement these checks.
"""

from __future__ import annotations

import uuid

from app.core.dependencies import DbDep
from app.core.exceptions import ForbiddenError, NotFoundError
from app.modules.auth.dependencies import CurrentUserDep
from app.modules.projects.models import Project
from app.modules.projects.repository import ProjectRepository
from app.shared.enums import MemberRole, UserRole


class ProjectAccessPolicy:
    def __init__(self, *, min_member_role: MemberRole | None = None) -> None:
        self.min_member_role = min_member_role

    async def __call__(self, project_id: uuid.UUID, user: CurrentUserDep, db: DbDep) -> Project:
        repo = ProjectRepository(db)
        project = await repo.get(project_id)
        if project is None:
            raise NotFoundError("Project not found")
        if user.role == UserRole.admin:
            return project

        member = await repo.get_member(project_id, user.id)
        if member is None:
            raise ForbiddenError("You are not a member of this project")
        if self.min_member_role == MemberRole.lead and member.role != MemberRole.lead:
            raise ForbiddenError("Project lead access required")
        return project


require_project_view = ProjectAccessPolicy()
require_project_lead = ProjectAccessPolicy(min_member_role=MemberRole.lead)
