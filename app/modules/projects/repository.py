"""Project repository."""

from __future__ import annotations

import uuid

from sqlalchemy import Select, select
from sqlalchemy.orm import selectinload

from app.core.database import BaseRepository
from app.modules.projects.models import Project, ProjectMember


class ProjectRepository(BaseRepository[Project]):
    model = Project

    async def get_with_members(self, project_id: uuid.UUID) -> Project | None:
        stmt = (
            self._query()
            .where(Project.id == project_id)
            .options(selectinload(Project.members).selectinload(ProjectMember.user))
        )
        result = await self.db.execute(stmt)
        return result.scalar_one_or_none()

    def list_query(
        self, *, user_id: uuid.UUID | None = None, search: str | None = None
    ) -> Select[tuple[Project]]:
        """All projects, optionally scoped to those a user is a member of."""
        stmt = self._query()
        if user_id is not None:
            stmt = stmt.join(ProjectMember, ProjectMember.project_id == Project.id).where(
                ProjectMember.user_id == user_id
            )
        if search:
            stmt = stmt.where(Project.name.ilike(f"%{search}%"))
        return stmt

    async def get_member(self, project_id: uuid.UUID, user_id: uuid.UUID) -> ProjectMember | None:
        stmt = (
            select(ProjectMember)
            .where(ProjectMember.project_id == project_id, ProjectMember.user_id == user_id)
            .options(selectinload(ProjectMember.user))
        )
        result = await self.db.execute(stmt)
        return result.scalar_one_or_none()

    async def is_member(self, project_id: uuid.UUID, user_id: uuid.UUID) -> bool:
        stmt = select(ProjectMember.id).where(
            ProjectMember.project_id == project_id, ProjectMember.user_id == user_id
        )
        result = await self.db.execute(stmt)
        return result.scalar_one_or_none() is not None

    async def add_member(self, member: ProjectMember) -> ProjectMember:
        self.db.add(member)
        await self.db.flush()
        return member

    async def remove_member(self, member: ProjectMember) -> None:
        await self.db.delete(member)
        await self.db.flush()
