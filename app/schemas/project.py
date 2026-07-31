from datetime import date, datetime

from pydantic import BaseModel, ConfigDict, Field

from app.models import MemberRole, ProjectStatus
from app.schemas.user import UserOut


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
    user_id: int
    role: MemberRole = MemberRole.contributor


class MemberOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    user_id: int
    role: MemberRole
    user: UserOut


class ProjectOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    name: str
    description: str | None
    status: ProjectStatus
    start_date: date | None
    end_date: date | None
    created_by: int
    created_at: datetime
    updated_at: datetime


class ProjectDetailOut(ProjectOut):
    members: list[MemberOut]
