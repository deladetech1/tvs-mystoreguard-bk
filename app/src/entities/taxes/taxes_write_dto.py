from typing import Optional
from decimal import Decimal
from pydantic import BaseModel, Field
from src.entities.taxes.taxes_base import TaxBase


# =====================================================
# CREATE TAX WRITE DTOs
# =====================================================

class CreateTaxWriteBase(TaxBase):
    """Base write DTO for creating a tax"""
    pass


class CreateTaxControllerWriteDto(CreateTaxWriteBase):
    """Controller DTO for creating a tax"""
    pass


class CreateTaxServiceWriteDto(CreateTaxWriteBase):
    """Service DTO for creating a tax"""
    pass


# =====================================================
# UPDATE TAX WRITE DTOs
# =====================================================

class UpdateTaxWriteBase(BaseModel):
    """Base write DTO for updating a tax"""
    name: Optional[str] = Field(None, min_length=1, max_length=255, description="Name of the tax")
    rate: Optional[Decimal] = Field(None, decimal_places=2, ge=0, le=100, description="Tax rate as a percentage (0-100)")
    description: Optional[str] = Field(None, max_length=1000, description="Description of the tax")
    is_active: Optional[bool] = Field(None, description="Whether the tax is active")
    is_inclusive: Optional[bool] = Field(None, description="Whether the tax is inclusive (included in the price)")


class UpdateTaxControllerWriteDto(UpdateTaxWriteBase):
    """Controller DTO for updating a tax"""
    pass


class UpdateTaxServiceWriteDto(UpdateTaxWriteBase):
    """Service DTO for updating a tax"""
    pass


# =====================================================
# DELETE TAX WRITE DTOs
# =====================================================

class DeleteTaxWriteBase(BaseModel):
    """Base write DTO for deleting a tax"""
    tax_id: str = Field(..., description="ID of the tax to delete")


class DeleteTaxControllerWriteDto(DeleteTaxWriteBase):
    """Controller DTO for deleting a tax"""
    pass


class DeleteTaxServiceWriteDto(DeleteTaxWriteBase):
    """Service DTO for deleting a tax"""
    pass

