from sqlalchemy import select
from sqlalchemy.orm import Session, selectinload

from app.models import Project, ProjectMember


class ProjectRepository:
    def __init__(self, db: Session):
        self.db = db

    def get(self, project_id: int) -> Project | None:
        return self.db.get(Project, project_id)

    def get_with_members(self, project_id: int) -> Project | None:
        return self.db.scalar(
            select(Project)
            .options(selectinload(Project.members).selectinload(ProjectMember.user))
            .where(Project.id == project_id)
        )

    def list_all(self) -> list[Project]:
        return list(self.db.scalars(select(Project).order_by(Project.created_at.desc())))

    def list_for_user(self, user_id: int) -> list[Project]:
        return list(
            self.db.scalars(
                select(Project)
                .join(ProjectMember, ProjectMember.project_id == Project.id)
                .where(ProjectMember.user_id == user_id)
                .order_by(Project.created_at.desc())
            )
        )

    def create(self, project: Project) -> Project:
        self.db.add(project)
        self.db.flush()
        return project

    def delete(self, project: Project) -> None:
        self.db.delete(project)

    # --- membership ---

    def get_member(self, project_id: int, user_id: int) -> ProjectMember | None:
        return self.db.scalar(
            select(ProjectMember).where(
                ProjectMember.project_id == project_id, ProjectMember.user_id == user_id
            )
        )

    def is_member(self, project_id: int, user_id: int) -> bool:
        return self.get_member(project_id, user_id) is not None

    def add_member(self, member: ProjectMember) -> ProjectMember:
        self.db.add(member)
        self.db.flush()
        return member

    def remove_member(self, member: ProjectMember) -> None:
        self.db.delete(member)
