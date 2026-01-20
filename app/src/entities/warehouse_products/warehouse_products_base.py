from typing import Optional
from typing_extensions import Literal
from pydantic import BaseModel, Field


# =====================================================
# ENUMS AND LITERALS
# =====================================================

DeleteStatusType = Literal['PENDING', 'DELETED', 'NOT_DELETED']
LocationType = Literal['STORE', 'WAREHOUSE']


# =====================================================
# WAREHOUSE PRODUCT BASE DTOs
# =====================================================

class WarehouseProductBase(BaseModel):
    """Base DTO for warehouse product information"""
    product_id: str = Field(..., description="Product ID")
    current_qty: int = Field(..., ge=0, description="Current quantity in warehouse")
    comment: Optional[str] = Field(None, description="Comment")
    reorder_level: int = Field(default=0, ge=0, description="Reorder level")
    reorder_quantity: int = Field(default=0, ge=0, description="Reorder quantity")
    is_active: bool = Field(default=True, description="Whether the warehouse product is active")

