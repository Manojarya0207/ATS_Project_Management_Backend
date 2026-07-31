from datetime import datetime

from pydantic import BaseModel, ConfigDict

from app.schemas.user import UserOut


class FileOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    task_id: int
    uploaded_by: int
    original_filename: str
    content_type: str | None
    size_bytes: int
    uploader: UserOut
    created_at: datetime
