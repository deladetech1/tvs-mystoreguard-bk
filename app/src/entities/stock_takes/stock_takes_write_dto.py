from typing import Optional, List
from pydantic import BaseModel, Field
from src.entities.stock_takes.stock_takes_base import (
    StockTakeBase,
    StockTakeItemCountBase,
    ResolutionStatus,
)


# =====================================================
# CREATE STOCK TAKE WRITE DTOs
# =====================================================

class CreateStockTakeWriteBase(StockTakeBase):
    """Base write DTO for creating a stock take with its counted lines."""
    items: List[StockTakeItemCountBase] = Field(
        ..., min_length=1, description="One or more counted product lines"
    )


class CreateStockTakeControllerWriteDto(CreateStockTakeWriteBase):
    """Controller DTO for creating a stock take."""
    pass


class CreateStockTakeServiceWriteDto(CreateStockTakeWriteBase):
    """Service DTO for creating a stock take."""
    pass


# =====================================================
# RESOLVE STOCK TAKE ITEM WRITE DTOs
# =====================================================

class ResolveStockTakeItemWriteBase(BaseModel):
    """Base write DTO for advancing the investigation of a counted line.

    resolution_status moves the line through PENDING -> INVESTIGATING -> RESOLVED.
    adjustment_qty is an OPTIONAL stock correction applied only when the line is
    RESOLVED, and only for CONFIRMED LOSSES:
      * negative  -> reduce stock by that amount (deducted FIFO from the location's
                     delivery breakdown; logged as a loss; the purchase pool is left
                     untouched because lost stock does not return to it)
      * 0         -> leave stock unchanged (default; e.g. a recount where the system
                     was right). Always pair with a resolution_note.
      * positive  -> REJECTED. A surplus is an unrecorded delivery; record it via the
                     Add Stock flow so cost/expiry land on a proper batch.
    """
    resolution_status: ResolutionStatus = Field(..., description="New resolution status for the line")
    resolution_note: Optional[str] = Field(None, description="Investigation outcome / explanation")
    adjustment_qty: int = Field(
        default=0,
        description="Confirmed-loss correction on RESOLVED: negative reduces stock, 0 = no change. "
                    "Positive is rejected (record surplus deliveries via Add Stock).",
    )


class ResolveStockTakeItemControllerWriteDto(ResolveStockTakeItemWriteBase):
    """Controller DTO for resolving a stock take item."""
    pass


class ResolveStockTakeItemServiceWriteDto(ResolveStockTakeItemWriteBase):
    """Service DTO for resolving a stock take item."""
    pass
