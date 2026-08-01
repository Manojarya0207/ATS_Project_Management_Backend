"""Feature modules.

Importing this package registers every SQLAlchemy model with ``Base.metadata``
— Alembic's ``env.py`` and the test-suite ``create_all`` rely on this.
"""

from app.modules.auth import models as auth_models
from app.modules.notifications import models as notification_models
from app.modules.projects import models as project_models
from app.modules.tasks import models as task_models
from app.modules.users import models as user_models

__all__ = [
    "auth_models",
    "notification_models",
    "project_models",
    "task_models",
    "user_models",
]
