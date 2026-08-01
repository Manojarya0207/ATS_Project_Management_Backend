"""Test data factories — build persisted domain objects with sensible defaults."""

from __future__ import annotations

import uuid
from datetime import date

from app.modules.projects.models import Project, ProjectMember
from app.modules.tasks.models import Comment, Task
from app.modules.users.models import User
from app.shared.enums import MemberRole, ProjectStatus, TaskPriority, TaskStatus
from sqlalchemy.ext.asyncio import AsyncSession


async def make_project(
    db: AsyncSession,
    *,
    creator: User,
    name: str = "Test Project",
    status: ProjectStatus = ProjectStatus.active,
    start_date: date | None = None,
    end_date: date | None = None,
) -> Project:
    project = Project(
        name=name,
        description="factory project",
        status=status,
        start_date=start_date,
        end_date=end_date,
        created_by=creator.id,
    )
    db.add(project)
    await db.commit()
    return project


async def make_member(
    db: AsyncSession,
    *,
    project: Project,
    user: User,
    role: MemberRole = MemberRole.contributor,
) -> ProjectMember:
    member = ProjectMember(project_id=project.id, user_id=user.id, role=role)
    db.add(member)
    await db.commit()
    return member


async def make_task(
    db: AsyncSession,
    *,
    project: Project,
    creator: User,
    title: str = "Test Task",
    status: TaskStatus = TaskStatus.todo,
    priority: TaskPriority = TaskPriority.medium,
    assignee_id: uuid.UUID | None = None,
    due_date: date | None = None,
    position: float = 1000.0,
) -> Task:
    task = Task(
        project_id=project.id,
        title=title,
        status=status,
        priority=priority,
        assignee_id=assignee_id,
        due_date=due_date,
        position=position,
        created_by=creator.id,
    )
    db.add(task)
    await db.commit()
    return task


async def make_comment(
    db: AsyncSession, *, task: Task, user: User, content: str = "A comment"
) -> Comment:
    comment = Comment(task_id=task.id, user_id=user.id, content=content)
    db.add(comment)
    await db.commit()
    return comment
