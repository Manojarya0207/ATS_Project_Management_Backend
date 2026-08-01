"""Comment business logic."""

from __future__ import annotations

import uuid
from collections.abc import Sequence

from sqlalchemy.ext.asyncio import AsyncSession

from app.core.exceptions import ForbiddenError, NotFoundError
from app.modules.tasks.models import Comment
from app.modules.tasks.repository import CommentRepository
from app.modules.tasks.schemas import CommentCreate, CommentUpdate
from app.modules.users.models import User
from app.shared.enums import UserRole
from app.shared.pagination import PageParams, PaginationMeta, paginate


class CommentService:
    def __init__(self, db: AsyncSession) -> None:
        self.db = db
        self.comments = CommentRepository(db)

    async def list_for_task(
        self, task_id: uuid.UUID, params: PageParams
    ) -> tuple[Sequence[Comment], PaginationMeta]:
        stmt = self.comments.list_for_task_query(task_id)
        return await paginate(self.db, stmt, params)

    async def create(self, task_id: uuid.UUID, payload: CommentCreate, actor: User) -> Comment:
        comment = await self.comments.add(
            Comment(task_id=task_id, user_id=actor.id, content=payload.content)
        )
        loaded = await self.comments.get(comment.id)
        assert loaded is not None
        return loaded

    async def update(self, comment_id: uuid.UUID, payload: CommentUpdate, actor: User) -> Comment:
        comment = await self._get_owned(comment_id, actor)
        comment.content = payload.content
        await self.db.flush()
        await self.db.refresh(comment)  # reload server-generated updated_at
        return comment

    async def delete(self, comment_id: uuid.UUID, actor: User) -> uuid.UUID:
        """Delete a comment, returning its task_id (for access verification)."""
        comment = await self._get_owned(comment_id, actor)
        task_id = comment.task_id
        await self.comments.delete(comment)  # soft delete
        return task_id

    async def get(self, comment_id: uuid.UUID) -> Comment:
        comment = await self.comments.get(comment_id)
        if comment is None:
            raise NotFoundError("Comment not found")
        return comment

    async def _get_owned(self, comment_id: uuid.UUID, actor: User) -> Comment:
        comment = await self.get(comment_id)
        if actor.role != UserRole.admin and comment.user_id != actor.id:
            raise ForbiddenError("You can only modify your own comments")
        return comment
