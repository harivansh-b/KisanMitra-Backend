from datetime import datetime
from typing import Optional
from pydantic import BaseModel, ConfigDict

from app.utils.enums import DocumentOwnerType


class DocumentResponse(BaseModel):
    id: str
    owner_id: str
    owner_type: DocumentOwnerType
    bucket: str
    path: str
    file_name: str
    content_type: str
    size: int
    url: Optional[str] = None
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)
