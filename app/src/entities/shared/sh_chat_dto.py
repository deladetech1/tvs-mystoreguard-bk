from typing import Optional
from datetime import datetime
from pydantic import BaseModel


class DeletionChatHistoryReadDto(BaseModel):
    """Read DTO for deletion chat history"""
    id: str
    resource_id: str
    message: str
    sent_by: str
    cdate: str
    ctime: str
    cdatetime: datetime
