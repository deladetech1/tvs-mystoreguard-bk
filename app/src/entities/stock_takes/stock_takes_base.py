from typing import Optional
from typing_extensions import Literal
from pydantic import BaseModel, Field


# =====================================================
# ENUMS AND LITERALS
# =====================================================

LocationType = Literal['STORE', 'WAREHOUSE']
StockTakeStatus = Literal['DRAFT', 'COMPLETED', 'CANCELLED']
MatchStatus = Literal['MATCH', 'OVER', 'SHORT']
ResolutionStatus = Literal['PENDING', 'INVESTIGATING', 'RESOLVED']


# =====================================================
# STOCK TAKE BASE DTOs
# =====================================================

class StockTakeItemCountBase(BaseModel):
    """A single counted line submitted when creating a stock take."""
    product_id: str = Field(..., description="Product ID being counted")
    counted_qty: int = Field(..., ge=0, description="Physically counted quantity")
    note: Optional[str] = Field(None, description="Optional note for this counted line")


class StockTakeBase(BaseModel):
    """Shared header fields for a stock take."""
    location_type: LocationType = Field(..., description="Whether the count is for a STORE or WAREHOUSE location")
    description: Optional[str] = Field(None, description="Optional description / reason for this stock take")
