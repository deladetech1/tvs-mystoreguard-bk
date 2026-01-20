from typing import Optional, List
from pydantic import BaseModel
from fastapi import Header, HTTPException


class AuthBaseWriteDto(BaseModel):
    """Base DTO for auth operations"""
    token: Optional[str] = None
    user_id: str
    tenant_id: str


class GlobalWriteBaseDto(BaseModel):
    """Global base DTO for all write/update/delete operations - includes org_id, bus_id, loc_id"""
    org_id: str
    bus_id: str
    loc_id: str
