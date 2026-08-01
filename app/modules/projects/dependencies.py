"""Project module dependency providers."""

from __future__ import annotations

from typing import Annotated

from fastapi import Depends

from app.core.dependencies import DbDep, EventBusDep
from app.modules.projects.service import ProjectService


def get_project_service(db: DbDep, event_bus: EventBusDep) -> ProjectService:
    return ProjectService(db, event_bus)


ProjectServiceDep = Annotated[ProjectService, Depends(get_project_service)]
