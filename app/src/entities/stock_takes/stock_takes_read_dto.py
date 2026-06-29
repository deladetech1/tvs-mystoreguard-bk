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
    image_urls: List[str] = Field(default_factory=list, description="Presigned image URLs for the product")
    counted_qty: int
    system_qty: int = Field(..., description="On-hand qty the system believed at count time")
    variance_qty: int = Field(..., description="counted_qty - system_qty (negative = short, positive = over)")
    unit_price: Optional[float] = Field(None, description="Unit price snapshotted at count time")
    currency_id: Optional[str] = Field(None, description="Currency id snapshot for this line")
    currency_name: Optional[str] = Field(None, description="Currency name snapshot for this line")
    currency_symbol: Optional[str] = Field(None, description="Currency symbol snapshot for this line")
    variance_value: Optional[float] = Field(
        None, description="Value of the variance = variance_qty * unit_price (null if no price given)"
    )
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


# =====================================================
# EDIT READ DTOs
# =====================================================

class EditStockTakeServiceReadDto(StockTakeReadDto):
    """Full stock take returned after an edit."""
    pass


class EditStockTakeControllerReadDto(StockTakeReadDto):
    """Full stock take returned after an edit."""
    pass


# =====================================================
# STATISTICS READ DTOs
# =====================================================

class CurrencyMoneyDto(BaseModel):
    """Money roll-ups for one currency. Values are never summed across currencies."""
    currency_id: Optional[str] = None
    currency_name: Optional[str] = None
    currency_symbol: Optional[str] = None
    total_shortage_value: float = Field(0, description="Value short, positive magnitude")
    total_overage_value: float = Field(0, description="Value over, positive magnitude")
    net_variance_value: float = Field(0, description="Overage minus shortage; negative = net short")
    total_corrected_value: float = Field(0, description="Value of stock corrected via resolutions, positive magnitude")


class TopShortageProductDto(BaseModel):
    """A product ranked by how much value it is short, in its line's currency."""
    product_id: str
    product_name: Optional[str] = None
    short_qty: int = Field(0, description="Total units short (positive magnitude)")
    shortage_value: float = Field(0, description="Total shortage value (positive magnitude)")
    currency_id: Optional[str] = None
    currency_name: Optional[str] = None
    currency_symbol: Optional[str] = None


class StockTakeStatisticsReadDto(BaseModel):
    """Aggregate stock-take statistics for a location."""
    # Counts (currency-independent)
    total_stock_takes: int = 0
    draft: int = 0
    completed: int = 0
    cancelled: int = 0
    total_lines: int = 0
    matched: int = 0
    over: int = 0
    short: int = 0
    unresolved_variances: int = 0
    # Accuracy
    accuracy_rate: float = Field(0, description="Matched lines / total lines, as a percentage (0-100)")
    # Money — grouped per currency; lines without unit_price are excluded
    money_by_currency: List[CurrencyMoneyDto] = Field(default_factory=list)
    # Worst offenders (each carries its own currency)
    top_shortage_products: List[TopShortageProductDto] = Field(default_factory=list)


class StockTakeStatisticsControllerReadDto(StockTakeStatisticsReadDto):
    pass
