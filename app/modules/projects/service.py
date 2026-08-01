"""Project business logic."""

from __future__ import annotations

import uuid
from collections.abc import Sequence

from sqlalchemy.ext.asyncio import AsyncSession

from app.core.constants import ErrorCode
from app.core.exceptions import ConflictError, NotFoundError
from app.modules.projects.models import Project, ProjectMember
from app.modules.projects.repository import ProjectRepository
from app.modules.projects.schemas import MemberAdd, ProjectCreate, ProjectUpdate
from app.modules.users.models import User
from app.modules.users.repository import UserRepository
from app.shared.enums import UserRole
from app.shared.events import EventBus, MemberAddedToProject
from app.shared.pagination import PageParams, PaginationMeta, apply_sort, paginate


class ProjectService:
    def __init__(self, db: AsyncSession, event_bus: EventBus) -> None:
        self.db = db
        self.event_bus = event_bus
        self.projects = ProjectRepository(db)
        self.users = UserRepository(db)

    async def list_projects(
        self, actor: User, params: PageParams
    ) -> tuple[Sequence[Project], PaginationMeta]:
        scope_user = None if actor.role == UserRole.admin else actor.id
        stmt = self.projects.list_query(user_id=scope_user, search=params.search)
        stmt = apply_sort(
            stmt,
            params,
            sortable={
                "name": Project.name,
                "status": Project.status,
                "start_date": Project.start_date,
                "end_date": Project.end_date,
                "created_at": Project.created_at,
            },
            default=Project.created_at,
        )
        if params.sort is None:
            # Preserve the original newest-first default ordering.
            stmt = stmt.order_by(None).order_by(Project.created_at.desc())
        return await paginate(self.db, stmt, params)

    async def get_project_detail(self, project_id: uuid.UUID) -> Project:
        """Load a project with members eager-loaded (access already enforced
        by ProjectAccessPolicy at the route layer)."""
        project = await self.projects.get_with_members(project_id)
        if project is None:
            raise NotFoundError("Project not found")
        return project

    async def create_project(self, payload: ProjectCreate, actor: User) -> Project:
        project = Project(**payload.model_dump(), created_by=actor.id)
        return await self.projects.add(project)

    async def update_project(self, project_id: uuid.UUID, payload: ProjectUpdate) -> Project:
        project = await self.projects.get(project_id)
        if project is None:
            raise NotFoundError("Project not found")
        for field, value in payload.model_dump(exclude_unset=True).items():
            setattr(project, field, value)
        await self.db.flush()
        return await self.get_project_detail(project_id)

    async def delete_project(self, project_id: uuid.UUID) -> None:
        project = await self.projects.get(project_id)
        if project is None:
            raise NotFoundError("Project not found")
        await self.projects.delete(project)  # soft delete

    # --- membership -----------------------------------------------------------

    async def add_member(
        self, project_id: uuid.UUID, payload: MemberAdd, actor: User
    ) -> ProjectMember:
        project = await self.projects.get(project_id)
        if project is None:
            raise NotFoundError("Project not found")
        user = await self.users.get(payload.user_id)
        if user is None:
            raise NotFoundError("User not found")
        if await self.projects.is_member(project_id, payload.user_id):
            raise ConflictError(
                "User is already a member of this project", code=ErrorCode.already_member
            )

        await self.projects.add_member(
            ProjectMember(project_id=project_id, user_id=payload.user_id, role=payload.role)
        )
        await self.event_bus.publish(
            MemberAddedToProject(
                project_id=project_id,
                project_name=project.name,
                user_id=payload.user_id,
                actor_id=actor.id,
            ),
            self.db,
        )
        # Reload with the user relationship for the response.
        loaded = await self.projects.get_member(project_id, payload.user_id)
        assert loaded is not None
        return loaded

    async def remove_member(self, project_id: uuid.UUID, user_id: uuid.UUID) -> None:
        member = await self.projects.get_member(project_id, user_id)
        if member is None:
            raise NotFoundError("Member not found")
        await self.projects.remove_member(member)
