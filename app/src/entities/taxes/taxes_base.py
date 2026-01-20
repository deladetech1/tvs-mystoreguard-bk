from typing import Optional
from decimal import Decimal
from pydantic import BaseModel, Field


# =====================================================
# TAX BASE DTOs
# =====================================================

class TaxBase(BaseModel):
    """Base DTO for tax information"""
    name: str = Field(..., min_length=1, max_length=255, description="Name of the tax")
    rate: Decimal = Field(..., decimal_places=2, ge=0, le=100, description="Tax rate as a percentage (0-100)")
    description: Optional[str] = Field(None, max_length=1000, description="Description of the tax")
    is_active: bool = Field(default=True, description="Whether the tax is active")
    is_inclusive: bool = Field(default=False, description="Whether the tax is inclusive (included in the price)")

