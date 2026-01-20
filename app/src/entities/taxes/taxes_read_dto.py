from typing import Optional
from datetime import datetime
from decimal import Decimal
from pydantic import BaseModel, Field
from src.entities.taxes.taxes_base import TaxBase


# =====================================================
# TAX READ DTOs
# =====================================================

class TaxReadBase(TaxBase):
    """Base read DTO for tax"""
    id: str
    tenant_id: str
    org_id: str
    bus_id: str
    cdate: Optional[str] = None
    ctime: Optional[str] = None
    cdatetime: Optional[datetime] = None
    created_by: Optional[str] = None
    updated_by: Optional[str] = None
    deleted_by: Optional[str] = None


class CreateTaxControllerReadDto(TaxReadBase):
    """Controller DTO for create tax read operations"""
    pass


class CreateTaxServiceReadDto(TaxReadBase):
    """Service DTO for create tax read operations"""
    pass


class UpdateTaxControllerReadDto(TaxReadBase):
    """Controller DTO for update tax read operations"""
    pass


class UpdateTaxServiceReadDto(TaxReadBase):
    """Service DTO for update tax read operations"""
    pass


class GetTaxControllerReadDto(TaxReadBase):
    """Controller DTO for get tax read operations"""
    pass


class GetTaxServiceReadDto(TaxReadBase):
    """Service DTO for get tax read operations"""
    pass


class GetTaxesControllerReadDto(TaxReadBase):
    """Controller DTO for get taxes list read operations"""
    pass


class GetTaxesServiceReadDto(TaxReadBase):
    """Service DTO for get taxes list read operations"""
    pass


class DeleteTaxReadBase(BaseModel):
    """Base read DTO for delete tax result"""
    tax_id: str
    message: str


class DeleteTaxControllerReadDto(DeleteTaxReadBase):
    """Controller DTO for delete tax read operations"""
    pass


class DeleteTaxServiceReadDto(DeleteTaxReadBase):
    """Service DTO for delete tax read operations"""
    pass


# =====================================================
# TAX STATISTICS READ DTOs
# =====================================================

class TaxStatisticsReadBase(BaseModel):
    """Base read DTO for tax statistics"""
    total_taxes: int = Field(default=0, description="Total number of taxes")
    total_active: int = Field(default=0, description="Total number of active taxes")
    total_inactive: int = Field(default=0, description="Total number of inactive taxes")
    average_rate: Optional[Decimal] = Field(default=None, description="Average tax rate across all taxes")
    highest_rate: Optional[Decimal] = Field(default=None, description="Highest tax rate")
    lowest_rate: Optional[Decimal] = Field(default=None, description="Lowest tax rate")
    total_inclusive: int = Field(default=0, description="Total number of inclusive taxes")
    total_exclusive: int = Field(default=0, description="Total number of exclusive taxes")


class GetTaxStatisticsControllerReadDto(TaxStatisticsReadBase):
    """Controller DTO for tax statistics"""
    pass


class GetTaxStatisticsServiceReadDto(TaxStatisticsReadBase):
    """Service DTO for tax statistics"""
    pass

