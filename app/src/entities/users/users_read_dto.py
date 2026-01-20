from typing import Optional, Any
from datetime import datetime
from pydantic import BaseModel, Field, model_validator


# =====================================================
# USER READ DTOs
# =====================================================

class UserReadBase(BaseModel):
    """Base read DTO for user - includes all fields from cp_users table"""
    id: str = Field(..., description="User ID")
    tenant_id: str = Field(..., description="Tenant ID")
    fullname: Optional[str] = Field(None, description="User's full name")
    contact: Optional[str] = Field(None, description="User's contact information")
    email: Optional[str] = Field(None, description="User's email address")
    username: Optional[str] = Field(None, description="Username")
    password: Optional[str] = Field(None, description="Password hash (excluded from responses)")
    is_active: Optional[bool] = Field(None, description="Whether the user is active")
    delete_status: Optional[str] = Field(None, description="Delete status")
    is_system: Optional[bool] = Field(None, description="Whether this is a system user")
    cdate: Optional[str] = None
    ctime: Optional[str] = None
    cdatetime: Optional[datetime] = None
    created_by: Optional[str] = None
    updated_by: Optional[str] = None
    deleted_by: Optional[str] = None
    
    # Allow additional fields that might exist in the table
    class Config:
        extra = "allow"
    
    @model_validator(mode='before')
    @classmethod
    def set_defaults(cls, data: Any) -> Any:
        """Set defaults for any additional fields from the database"""
        if isinstance(data, dict):
            # Ensure password is always None in response
            if 'password' in data:
                data['password'] = None
        return data


class GetUsersControllerReadDto(UserReadBase):
    """Controller DTO for get users read operations"""
    pass


class GetUsersServiceReadDto(UserReadBase):
    """Service DTO for get users read operations"""
    pass

