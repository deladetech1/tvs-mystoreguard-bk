from typing import Optional, List
from datetime import datetime
from pydantic import BaseModel, Field


# =====================================================
# STOCK TAKE ITEM READ DTOs
# =====================================================

class StockTakeItemReadDto(BaseModel):
    """A single counted line with its variance and resolution state."""
    id: str
    stock_take_id: str
    product_id: str
    product_name: Optional[str] = Field(None, description="Product name (joined)")
    counted_qty: int
    system_qty: int = Field(..., description="On-hand qty the system believed at count time")
    variance_qty: int = Field(..., description="counted_qty - system_qty (negative = short, positive = over)")
    match_status: str = Field(..., description="MATCH | OVER | SHORT")
    resolution_status: str = Field(..., description="PENDING | INVESTIGATING | RESOLVED")
    note: Optional[str] = None
    resolution_note: Optional[str] = None
    adjustment_qty: int = Field(0, description="Signed stock correction applied at resolution")
    adjustment_movement_id: Optional[str] = None
    resolved_by: Optional[str] = None
    resolved_datetime: Optional[datetime] = None
    cdatetime: Optional[datetime] = None


# =====================================================
# STOCK TAKE HEADER READ DTOs
# =====================================================

class StockTakeVarianceSummary(BaseModel):
    """Roll-up of how a count turned out."""
    total_lines: int = 0
    matched: int = 0
    over: int = 0
    short: int = 0
    unresolved_variances: int = Field(0, description="OVER/SHORT lines not yet RESOLVED")


class StockTakeReadDto(BaseModel):
    """Stock take header, optionally with its counted lines."""
    id: str
    loc_id: str
    location_type: str
    stock_take_number: str
    status: str = Field(..., description="DRAFT | COMPLETED | CANCELLED")
    description: Optional[str] = None
    completed_datetime: Optional[datetime] = None
    completed_by: Optional[str] = None
    cdatetime: Optional[datetime] = None
    created_by: Optional[str] = None
    summary: Optional[StockTakeVarianceSummary] = None
    items: Optional[List[StockTakeItemReadDto]] = None


class CreateStockTakeServiceReadDto(StockTakeReadDto):
    pass


class CreateStockTakeControllerReadDto(StockTakeReadDto):
    pass


class GetStockTakeServiceReadDto(StockTakeReadDto):
    pass


class GetStockTakeControllerReadDto(StockTakeReadDto):
    pass


class GetStockTakesServiceReadDto(BaseModel):
    stock_takes: List[StockTakeReadDto] = []


class GetStockTakesControllerReadDto(GetStockTakesServiceReadDto):
    pass


# =====================================================
# RESOLVE / COMPLETE READ DTOs
# =====================================================

class ResolveStockTakeItemServiceReadDto(StockTakeItemReadDto):
    pass


class ResolveStockTakeItemControllerReadDto(StockTakeItemReadDto):
    pass


class CompleteStockTakeServiceReadDto(StockTakeReadDto):
    pass


class CompleteStockTakeControllerReadDto(StockTakeReadDto):
    pass
