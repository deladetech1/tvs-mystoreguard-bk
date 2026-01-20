from typing import Optional
from pydantic import BaseModel


class ApproveDeletionWriteDto(BaseModel):
    """Write DTO for approval deletion request"""
    resource_id: str
    action: str  # 'approve' or 'reject'
    reason: Optional[str] = None


class ApproveDeletionReadDto(BaseModel):
    """Read DTO for approval deletion response"""
    resource_id: str
    action: str
