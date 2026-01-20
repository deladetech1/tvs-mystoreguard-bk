from typing import Optional
from datetime import datetime
from decimal import Decimal
from pydantic import BaseModel, Field


# =====================================================
# UNIT OF MEASURE READ DTOs
# =====================================================

class UnitOfMeasureReadBase(BaseModel):
    """Base read DTO for unit of measure"""
    id: str
    tenant_id: str
    name: str
    symbol: str
    decimal_place: Decimal = Field(..., decimal_places=2, description="Number of decimal places")
    delete_status: str
    is_active: bool = Field(default=True, description="Whether the unit of measure is active")
    description: Optional[str] = None
    cdate: Optional[str] = None
    ctime: Optional[str] = None
    cdatetime: Optional[datetime] = None
    created_by: Optional[str] = None
    updated_by: Optional[str] = None
    deleted_by: Optional[str] = None


class GetUnitOfMeasuresControllerReadDto(UnitOfMeasureReadBase):
    """Controller DTO for get unit of measures read operations"""
    pass


class GetUnitOfMeasuresServiceReadDto(UnitOfMeasureReadBase):
    """Service DTO for get unit of measures read operations"""
    pass

