from typing import Optional
from typing_extensions import Literal
from pydantic import BaseModel, Field


# =====================================================
# ENUMS AND LITERALS
# =====================================================

DeleteStatusType = Literal['PENDING', 'DELETED', 'NOT_DELETED']
BatchStatusType = Literal['RECEIVED', 'PARTIALLY_ALLOCATED', 'FULLY_ALLOCATED', 'VOID', 'CANCELLED']
BatchType = Literal['PURCHASE', 'OPENING_STOCK', 'ADJUSTMENT']

# Product split (break-bulk) literals
SplitPriceModeType = Literal['AUTO', 'MANUAL']
SplitDestinationType = Literal['EXISTING', 'NEW']
SplitStatusType = Literal['ACTIVE', 'REVERSED']
# Where the source stock is drawn from:
#   PRODUCT   = the unallocated purchase-batch pool (qty_remaining), pre-distribution
#   STORE     = shelf stock at the current store location (batch_locations)
#   WAREHOUSE = shelf stock at the current warehouse location (batch_locations)
SplitSourceScopeType = Literal['PRODUCT', 'STORE', 'WAREHOUSE']


# =====================================================
# PRODUCT BASE DTOs
# =====================================================

class ProductBase(BaseModel):
    """Base DTO for product information"""
    name: str = Field(..., description="Product name")
    description: Optional[str] = Field(None, description="Product description")
    sku: Optional[str] = Field(None, description="Product SKU")
    bar_code: Optional[str] = Field(None, description="Product barcode")
    is_active: bool = Field(default=True, description="Whether the product is active")


# =====================================================
# PURCHASE BATCH BASE DTOs
# =====================================================

class PurchaseBatchBase(BaseModel):
    """Base DTO for purchase batch information"""
    supplier_id: Optional[str] = Field(None, description="Supplier ID")
    currency_id: str = Field(..., description="Currency ID")
    cost_price: float = Field(..., ge=0, description="Cost price")
    base_selling_price: float = Field(..., ge=0, description="Base selling price")
    product_size: Optional[str] = Field(None, description="Product size")
    unit_of_measure_id: Optional[str] = Field(None, description="Unit of measure ID")
    qty_received: int = Field(..., gt=0, description="Quantity received")
    qty_remaining: Optional[int] = Field(None, ge=0, description="Quantity remaining (only for products, not for store/warehouse products)")
    specific_product_per_batch_received_qty: int = Field(..., gt=0, description="Quantity received for this batch")
    specific_product_per_batch_remaining_qty: Optional[int] = Field(None, ge=0, description="Remaining quantity for this batch (only for products, not for store/warehouse products)")
    qty_at_location: Optional[int] = Field(None, ge=0, description="Quantity allocated to this specific location (store/warehouse). Only present in store/warehouse product responses.")
    product_expiry_date: Optional[str] = Field(None, description="Product expiry date (YYYY-MM-DD)")
    is_active: bool = Field(default=True, description="Whether the batch is active")
    status: BatchStatusType = Field(..., description="Batch status: RECEIVED, PARTIALLY_ALLOCATED, FULLY_ALLOCATED, VOID, or CANCELLED")
    batch_type: BatchType = Field(..., description="Batch type: PURCHASE (from supplier), OPENING_STOCK (initial/manual stock), or ADJUSTMENT (corrections)")

