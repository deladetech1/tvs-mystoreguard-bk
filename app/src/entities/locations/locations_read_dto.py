from typing import Optional
from datetime import datetime
from pydantic import BaseModel, Field


# =====================================================
# LOCATION READ DTOs
# =====================================================

class LocationReadBase(BaseModel):
    """Base read DTO for location"""
    id: str
    tenant_id: str
    loc_name: str
    delete_status: str
    is_active: bool = Field(default=True, description="Whether the location is active")
    description: Optional[str] = None
    cdate: Optional[str] = None
    ctime: Optional[str] = None
    cdatetime: Optional[datetime] = None
    created_by: Optional[str] = None
    updated_by: Optional[str] = None
    deleted_by: Optional[str] = None


class GetLocationsControllerReadDto(LocationReadBase):
    """Controller DTO for get locations read operations"""
    pass


class GetLocationsServiceReadDto(LocationReadBase):
    """Service DTO for get locations read operations"""
    pass

