from typing import Optional
from typing_extensions import Literal
from pydantic import BaseModel, Field


# =====================================================
# ENUMS AND LITERALS
# =====================================================

DeleteStatusType = Literal['PENDING', 'DELETED', 'NOT_DELETED']


# =====================================================
# CLIENT BASE DTOs
# =====================================================

class ClientBase(BaseModel):
    """Base DTO for client information"""
    fullname: str = Field(..., description="Client full name")
    email: Optional[str] = Field(None, description="Client email address")
    contact: Optional[str] = Field(None, description="Client contact/phone number")
    address: Optional[str] = Field(None, description="Client address")
    description: Optional[str] = Field(None, description="Additional description")
    is_active: bool = Field(default=True, description="Whether the client is active")


