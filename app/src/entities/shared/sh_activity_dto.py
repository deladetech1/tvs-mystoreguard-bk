from typing import Optional, List, Dict, Any
from datetime import datetime
from pydantic import BaseModel


class ActivityLogReadDto(BaseModel):
    """Read DTO for activity log"""
    log_id: str
    new_data: Optional[Dict[str, Any]] = None
    old_data: Optional[Dict[str, Any]] = None
    action: str
    performed_by_fullname: Optional[str] = None
    performed_by_email: Optional[str] = None
    performed_by_contact: Optional[str] = None
    cdate: Optional[str] = None
    ctime: Optional[str] = None
    cdatetime: Optional[datetime] = None


class ActivityResourceTypeReadDto(BaseModel):
    """Read DTO for available activity log resource types from cp_resource_types table"""
    id: str
    resource_type_name: str
    parent_resource_id: Optional[str] = None
    description: Optional[str] = None


class DeleteActivityLogsWriteDto(BaseModel):
    """Write DTO for deleting activity logs"""
    log_ids: List[str]


class DeleteActivityLogsReadDto(BaseModel):
    """Read DTO for delete activity logs result"""
    deleted_count: int
