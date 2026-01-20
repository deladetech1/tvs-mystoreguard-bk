from typing import Optional
from typing_extensions import Literal
from pydantic import BaseModel, Field


# =====================================================
# ENUMS AND LITERALS
# =====================================================

DeleteStatusType = Literal['PENDING', 'DELETED', 'NOT_DELETED']


# =====================================================
# CUSTOMER BASE DTOs
# =====================================================

class CustomerBase(BaseModel):
    """Base DTO for customer information"""
    fullname: str = Field(..., description="Customer full name")
    email: Optional[str] = Field(None, description="Customer email address")
    contact: Optional[str] = Field(None, description="Customer contact/phone number")
    address: Optional[str] = Field(None, description="Customer address")
    description: Optional[str] = Field(None, description="Additional description")
    is_active: bool = Field(default=True, description="Whether the customer is active")


