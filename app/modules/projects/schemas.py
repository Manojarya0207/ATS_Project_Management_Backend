"""Project schemas."""

from __future__ import annotations

import uuid
from datetime import date, datetime

from pydantic import BaseModel, ConfigDict, Field

from app.modules.users.schemas import UserOut
from app.shared.enums import MemberRole, ProjectStatus


class ProjectOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    name: str
    description: str | None
    status: ProjectStatus
    start_date: date | None
    end_date: date | None
    created_by: uuid.UUID
    created_at: datetime
    updated_at: datetime


class MemberOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    user_id: uuid.UUID
    role: MemberRole
    user: UserOut


class ProjectDetailOut(ProjectOut):
    members: list[MemberOut]


class ProjectCreate(BaseModel):
    name: str = Field(min_length=1, max_length=255)
    description: str | None = None
    status: ProjectStatus = ProjectStatus.planning
    start_date: date | None = None
    end_date: date | None = None


class ProjectUpdate(BaseModel):
    name: str | None = Field(default=None, min_length=1, max_length=255)
    description: str | None = None
    status: ProjectStatus | None = None
    start_date: date | None = None
    end_date: date | None = None


class MemberAdd(BaseModel):
    user_id: uuid.UUID
    role: MemberRole = MemberRole.contributor
