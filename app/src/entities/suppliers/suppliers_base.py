from typing import Optional
from typing_extensions import Literal
from pydantic import BaseModel, Field


# =====================================================
# ENUMS AND LITERALS
# =====================================================

DeleteStatusType = Literal['PENDING', 'DELETED', 'NOT_DELETED']


# =====================================================
# SUPPLIER BASE DTOs
# =====================================================

class SupplierBase(BaseModel):
    """Base DTO for supplier information"""
    fullname: str = Field(..., description="Supplier full name")
    email: Optional[str] = Field(None, description="Supplier email address")
    contact: Optional[str] = Field(None, description="Supplier contact/phone number")
    address: Optional[str] = Field(None, description="Supplier address")
    description: Optional[str] = Field(None, description="Additional description")
    is_active: bool = Field(default=True, description="Whether the supplier is active")

