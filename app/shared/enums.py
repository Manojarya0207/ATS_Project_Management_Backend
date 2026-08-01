"""Domain enums shared across modules.

Values are the API's public contract — they appear verbatim in request and
response payloads and are stored as strings in the database
(``native_enum=False``), so renaming a value is a breaking change.
"""

from __future__ import annotations

import enum


class UserRole(str, enum.Enum):
    admin = "admin"
    employee = "employee"


class ProjectStatus(str, enum.Enum):
    planning = "planning"
    active = "active"
    on_hold = "on_hold"
    completed = "completed"
    archived = "archived"


class MemberRole(str, enum.Enum):
    lead = "lead"
    contributor = "contributor"


class TaskStatus(str, enum.Enum):
    todo = "todo"
    in_progress = "in_progress"
    in_review = "in_review"
    done = "done"


class TaskPriority(str, enum.Enum):
    low = "low"
    medium = "medium"
    high = "high"
    urgent = "urgent"


class NotificationType(str, enum.Enum):
    project_membership = "project_membership"
    task_assignment = "task_assignment"
    general = "general"


class SortOrder(str, enum.Enum):
    asc = "asc"
    desc = "desc"
