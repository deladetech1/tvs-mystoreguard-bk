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
    unit_price: Optional[float] = Field(
        None, ge=0,
        description="Unit price for this line, supplied by the caller (price lives per "
                    "delivery, not on the product). Snapshotted so the variance can be valued.",
    )
    # Currency snapshotted per line: items in one count may be priced in different
    # currencies. Frozen as plain text so the take never shifts if the currency changes.
    currency_id: Optional[str] = Field(None, description="Currency id for this line (snapshot)")
    currency_name: Optional[str] = Field(None, description="Currency name for this line (snapshot)")
    currency_symbol: Optional[str] = Field(None, description="Currency symbol for this line (snapshot)")
    note: Optional[str] = Field(None, description="Optional note for this counted line")


class StockTakeBase(BaseModel):
    """Shared header fields for a stock take."""
    location_type: LocationType = Field(..., description="Whether the count is for a STORE or WAREHOUSE location")
    description: Optional[str] = Field(None, description="Optional description / reason for this stock take")
