from typing import Optional, List
from datetime import datetime, date
from pydantic import BaseModel, Field, ConfigDict
from src.entities.purchase_orders.purchase_orders_base import (
    PurchaseOrderBase,
    PurchaseOrderItemBase,
)
from src.entities.products.products_base import PurchaseBatchBase


# =====================================================
# CURRENCY READ DTO (for nested currency in items)
# =====================================================

class CurrencyReadDto(BaseModel):
    """Read DTO for currency information in purchase order items"""
    id: str = Field(..., description="Currency ID")
    name: Optional[str] = Field(None, description="Currency name")
    code: Optional[str] = Field(None, description="Currency code")
    symbol: Optional[str] = Field(None, description="Currency symbol")
    decimal_places: Optional[int] = Field(None, description="Currency decimal places")
    currency_position: Optional[str] = Field(None, description="Currency position (before/after)")


# =====================================================
# PURCHASE ORDER ITEM READ DTOs
# =====================================================

class PurchaseOrderItemReadDto(PurchaseOrderItemBase):
    """Read DTO for purchase order item"""
    model_config = ConfigDict(extra='ignore')
    
    id: str
    tenant_id: str
    org_id: str
    bus_id: str
    purchase_order_id: str
    qty_received: int = Field(default=0, ge=0, description="Received quantity")
    qty_remaining: int = Field(default=0, ge=0, description="Remaining quantity")
    # Joined fields from SQL JOINs
    product_name: Optional[str] = Field(None, description="Product name from JOIN")
    # Nested currency object
    currency: Optional[CurrencyReadDto] = Field(None, description="Currency information")
    # Nested batches (not in table)
    batches: Optional[List['PurchaseBatchReadDto']] = Field(default=None, description="Batches for this product")


# =====================================================
# PRODUCT MOVEMENT READ DTOs
# =====================================================

class ProductMovementReadDto(BaseModel):
    """Read DTO for product movement"""
    model_config = ConfigDict(extra='ignore')
    
    id: str
    tenant_id: str
    org_id: str
    bus_id: str
    product_id: str
    batch_id: Optional[str] = Field(None, description="Batch ID (if movement is related to a batch)")
    location_type: Optional[str] = Field(None, description="Location type")
    location_id: Optional[str] = Field(None, description="Location ID")
    movement_type: str = Field(..., description="Movement type: IN or OUT")
    qty: int = Field(..., gt=0, description="Quantity moved")
    reason: str = Field(..., description="Reason for movement (e.g., PURCHASE, SALE, ADJUSTMENT)")
    reference_id: Optional[str] = Field(None, description="Reference ID (e.g., receipt_id for purchases)")
    cdate: Optional[str] = Field(None, description="Creation date")
    ctime: Optional[str] = Field(None, description="Creation time")
    cdatetime: datetime
    created_by: Optional[str] = Field(None, description="Creator fullname")


# =====================================================
# PURCHASE BATCH READ DTOs
# =====================================================

class PurchaseBatchReadDto(PurchaseBatchBase):
    """Read DTO for purchase batch"""
    model_config = ConfigDict(extra='ignore')
    
    id: str
    tenant_id: str
    org_id: str
    bus_id: str
    product_id: str
    batch_type: str = Field(..., description="Batch type: PURCHASE, OPENING_STOCK, or ADJUSTMENT")
    batch_number: Optional[str] = Field(None, description="Batch number")
    delete_status: str
    cdate: Optional[str] = Field(None, description="Creation date")
    ctime: Optional[str] = Field(None, description="Creation time")
    cdatetime: datetime
    created_by: Optional[str] = None
    updated_by: Optional[str] = None
    deleted_by: Optional[str] = None
    # Joined fields from related tables
    currency_name: Optional[str] = Field(None, description="Currency name from JOIN")
    currency_code: Optional[str] = Field(None, description="Currency code from JOIN")
    currency_symbol: Optional[str] = Field(None, description="Currency symbol from JOIN")
    currency_decimal_places: Optional[int] = Field(None, description="Currency decimal places from JOIN")
    currency_position: Optional[str] = Field(None, description="Currency position from JOIN")
    unit_of_measure_name: Optional[str] = Field(None, description="Unit of measure name from JOIN")
    supplier_name: Optional[str] = Field(None, description="Supplier fullname from JOIN")
    # Receipt information (for PURCHASE batches)
    receipt: Optional['PurchaseReceiptForBatchReadDto'] = Field(None, description="Purchase receipt information for this batch")
    # Movements for this batch
    movements: Optional[List[ProductMovementReadDto]] = Field(default=None, description="Product movements for this batch")


# =====================================================
# PURCHASE ORDER READ DTOs
# =====================================================

class PurchaseOrderReadBase(PurchaseOrderBase):
    """Base read DTO for purchase order"""
    id: str
    tenant_id: str
    org_id: str
    bus_id: str
    po_number: Optional[str] = Field(None, description="Purchase order number (auto-generated)")
    cdatetime: datetime
    created_by: Optional[str] = None
    supplier_name: Optional[str] = Field(None, description="Supplier fullname")
    assign_to_name: Optional[str] = Field(None, description="Assigned user fullname")


class PurchaseOrderWithItemsReadDto(BaseModel):
    """Read DTO for purchase order with items"""
    purchase_order: PurchaseOrderReadBase = Field(..., description="Purchase order information")
    items: List[PurchaseOrderItemReadDto] = Field(default_factory=list, description="List of purchase order items")


class CreatePurchaseOrderControllerReadDto(PurchaseOrderWithItemsReadDto):
    """Controller DTO for create purchase order read operations"""
    pass


class CreatePurchaseOrderServiceReadDto(PurchaseOrderWithItemsReadDto):
    """Service DTO for create purchase order read operations"""
    pass


class UpdatePurchaseOrderControllerReadDto(PurchaseOrderWithItemsReadDto):
    """Controller DTO for update purchase order read operations"""
    pass


class UpdatePurchaseOrderServiceReadDto(PurchaseOrderWithItemsReadDto):
    """Service DTO for update purchase order read operations"""
    pass


class GetPurchaseOrderControllerReadDto(PurchaseOrderWithItemsReadDto):
    """Controller DTO for get purchase order read operations"""
    pass


class GetPurchaseOrderServiceReadDto(PurchaseOrderWithItemsReadDto):
    """Service DTO for get purchase order read operations"""
    pass


class GetPurchaseOrdersControllerReadDto(PurchaseOrderWithItemsReadDto):
    """Controller DTO for get purchase orders list read operations"""
    pass


class GetPurchaseOrdersServiceReadDto(PurchaseOrderWithItemsReadDto):
    """Service DTO for get purchase orders list read operations"""
    pass


class CancelPurchaseOrderReadBase(BaseModel):
    """Base read DTO for cancel purchase order result"""
    purchase_order_id: str
    message: str


class CancelPurchaseOrderControllerReadDto(CancelPurchaseOrderReadBase):
    """Controller DTO for cancel purchase order read operations"""
    pass


class CancelPurchaseOrderServiceReadDto(CancelPurchaseOrderReadBase):
    """Service DTO for cancel purchase order read operations"""
    pass


class PermanentDeletePurchaseOrderReadBase(BaseModel):
    """Base read DTO for permanent delete purchase order result"""
    purchase_order_id: str
    message: str


class PermanentDeletePurchaseOrderControllerReadDto(PermanentDeletePurchaseOrderReadBase):
    """Controller DTO for permanent delete purchase order read operations"""
    pass


class PermanentDeletePurchaseOrderServiceReadDto(PermanentDeletePurchaseOrderReadBase):
    """Service DTO for permanent delete purchase order read operations"""
    pass


# =====================================================
# PURCHASE RECEIPT READ DTOs
# =====================================================

class PurchaseReceiptReadBase(BaseModel):
    """Base read DTO for purchase receipt"""
    id: str
    tenant_id: str
    org_id: str
    bus_id: str
    purchase_order_id: str
    receipt_number: str = Field(..., description="Receipt number (auto-generated)")
    received_date: date = Field(..., description="Date when items were received")
    description: Optional[str] = Field(None, description="Receipt description")
    status: str = Field(..., description="Receipt status")
    cdatetime: datetime
    created_by: Optional[str] = None


class PurchaseReceiptForBatchReadDto(BaseModel):
    """Simplified receipt DTO for batch responses"""
    id: str
    receipt_number: str
    received_date: date
    description: Optional[str] = None
    status: str
    cdatetime: datetime


class ReceivePurchaseOrderControllerReadDto(PurchaseOrderWithItemsReadDto):
    """Controller DTO for receive purchase order read operations"""
    receipt: Optional[PurchaseReceiptReadBase] = Field(None, description="Receipt information")


class ReceivePurchaseOrderServiceReadDto(PurchaseOrderWithItemsReadDto):
    """Service DTO for receive purchase order read operations"""
    receipt: Optional[PurchaseReceiptReadBase] = Field(None, description="Receipt information")


class GetPurchaseReceiptControllerReadDto(PurchaseReceiptReadBase):
    """Controller DTO for get purchase receipt read operations"""
    created_by_name: Optional[str] = Field(None, description="Creator fullname")


class GetPurchaseReceiptServiceReadDto(PurchaseReceiptReadBase):
    """Service DTO for get purchase receipt read operations"""
    created_by_name: Optional[str] = Field(None, description="Creator fullname")


class GetPurchaseReceiptsControllerReadDto(PurchaseReceiptReadBase):
    """Controller DTO for get purchase receipts list read operations"""
    created_by_name: Optional[str] = Field(None, description="Creator fullname")
    purchase_order_number: Optional[str] = Field(None, description="Purchase order number")


class GetPurchaseReceiptsServiceReadDto(PurchaseReceiptReadBase):
    """Service DTO for get purchase receipts list read operations"""
    created_by_name: Optional[str] = Field(None, description="Creator fullname")
    purchase_order_number: Optional[str] = Field(None, description="Purchase order number")


class UpdatePurchaseReceiptControllerReadDto(PurchaseReceiptReadBase):
    """Controller DTO for update purchase receipt read operations"""
    created_by_name: Optional[str] = Field(None, description="Creator fullname")


class UpdatePurchaseReceiptServiceReadDto(PurchaseReceiptReadBase):
    """Service DTO for update purchase receipt read operations"""
    created_by_name: Optional[str] = Field(None, description="Creator fullname")


class DeletePurchaseReceiptReadBase(BaseModel):
    """Base read DTO for delete purchase receipt result"""
    receipt_id: str
    message: str


class DeletePurchaseReceiptControllerReadDto(DeletePurchaseReceiptReadBase):
    """Controller DTO for delete purchase receipt read operations"""
    pass


class DeletePurchaseReceiptServiceReadDto(DeletePurchaseReceiptReadBase):
    """Service DTO for delete purchase receipt read operations"""
    pass


# =====================================================
# PURCHASE ORDER STATISTICS READ DTOs
# =====================================================

class PurchaseOrderStatisticsReadBase(BaseModel):
    """Base read DTO for purchase order statistics"""
    total_purchase_orders: int = Field(default=0, description="Total number of purchase orders")
    total_items: int = Field(default=0, description="Total number of purchase order items")
    total_value: float = Field(default=0.0, description="Total value of all purchase orders (cost_price * qty_ordered)")
    total_received_value: float = Field(default=0.0, description="Total received value (cost_price * qty_received)")
    
    # By status
    total_draft: int = Field(default=0, description="Total purchase orders with status DRAFT")
    total_approved: int = Field(default=0, description="Total purchase orders with status APPROVED")
    total_partially_received: int = Field(default=0, description="Total purchase orders with status PARTIALLY_RECEIVED")
    total_received: int = Field(default=0, description="Total purchase orders with status RECEIVED")
    total_cancelled: int = Field(default=0, description="Total purchase orders with status CANCELLED")
    total_completed: int = Field(default=0, description="Total purchase orders with status COMPLETED")
    total_pending: int = Field(default=0, description="Total purchase orders with status PENDING")
    total_on_hold: int = Field(default=0, description="Total purchase orders with status ON_HOLD")
    total_in_progress: int = Field(default=0, description="Total purchase orders with status IN_PROGRESS")
    
    # Additional statistics
    average_order_value: Optional[float] = Field(default=None, description="Average order value")
    total_qty_ordered: int = Field(default=0, description="Total quantity ordered across all items")
    total_qty_received: int = Field(default=0, description="Total quantity received across all items")


class GetPurchaseOrderStatisticsControllerReadDto(PurchaseOrderStatisticsReadBase):
    """Controller DTO for purchase order statistics"""
    pass


class GetPurchaseOrderStatisticsServiceReadDto(PurchaseOrderStatisticsReadBase):
    """Service DTO for purchase order statistics"""
    pass


# Resolve forward references
PurchaseOrderItemReadDto.model_rebuild()
PurchaseBatchReadDto.model_rebuild()
