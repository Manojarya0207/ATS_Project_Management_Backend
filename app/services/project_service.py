from sqlalchemy.orm import Session

from app.models import Notification, Project, ProjectMember, User, UserRole
from app.repositories.misc_repository import NotificationRepository
from app.repositories.project_repository import ProjectRepository
from app.repositories.user_repository import UserRepository
from app.schemas.project import MemberAdd, ProjectCreate, ProjectUpdate
from app.utils.exceptions import ConflictError, ForbiddenError, NotFoundError


class ProjectService:
    def __init__(self, db: Session):
        self.db = db
        self.projects = ProjectRepository(db)
        self.users = UserRepository(db)
        self.notifications = NotificationRepository(db)

    def list_projects(self, user: User) -> list[Project]:
        # Admin sees all; employees only projects they belong to.
        if user.role == UserRole.admin:
            return self.projects.list_all()
        return self.projects.list_for_user(user.id)

    def get_project(self, user: User, project_id: int) -> Project:
        project = self.projects.get_with_members(project_id)
        if project is None:
            raise NotFoundError("Project not found")
        self._require_access(user, project_id)
        return project

    def create_project(self, user: User, data: ProjectCreate) -> Project:
        project = Project(**data.model_dump(), created_by=user.id)
        self.projects.create(project)
        return project

    def update_project(self, user: User, project_id: int, data: ProjectUpdate) -> Project:
        project = self.projects.get(project_id)
        if project is None:
            raise NotFoundError("Project not found")
        for field, value in data.model_dump(exclude_unset=True).items():
            setattr(project, field, value)
        self.db.flush()
        return self.projects.get_with_members(project_id)

    def delete_project(self, project_id: int) -> None:
        project = self.projects.get(project_id)
        if project is None:
            raise NotFoundError("Project not found")
        self.projects.delete(project)

    def add_member(self, project_id: int, data: MemberAdd) -> ProjectMember:
        project = self.projects.get(project_id)
        if project is None:
            raise NotFoundError("Project not found")
        user = self.users.get(data.user_id)
        if user is None:
            raise NotFoundError("User not found")
        if self.projects.is_member(project_id, data.user_id):
            raise ConflictError("User is already a member of this project")
        member = self.projects.add_member(
            ProjectMember(project_id=project_id, user_id=data.user_id, role=data.role)
        )
        self.notifications.create(
            Notification(
                user_id=data.user_id,
                title="Added to project",
                message=f'You have been added to project "{project.name}".',
            )
        )
        return member

    def remove_member(self, project_id: int, user_id: int) -> None:
        member = self.projects.get_member(project_id, user_id)
        if member is None:
            raise NotFoundError("Membership not found")
        self.projects.remove_member(member)

    def _require_access(self, user: User, project_id: int) -> None:
        if user.role == UserRole.admin:
            return
        if not self.projects.is_member(project_id, user.id):
            raise ForbiddenError("You are not a member of this project")
