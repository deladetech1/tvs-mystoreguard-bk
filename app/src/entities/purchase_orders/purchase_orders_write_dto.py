from typing import Optional, List
from datetime import date
from pydantic import BaseModel, Field
from src.entities.purchase_orders.purchase_orders_base import (
    PurchaseOrderBase,
    PurchaseOrderItemBase,
    PurchaseReceiptBase,
    PurchaseReceiptItemBase,
    PurchaseOrderStatusType,
)


# =====================================================
# CREATE PURCHASE ORDER WRITE DTOs
# =====================================================

class CreatePurchaseOrderItemWriteDto(PurchaseOrderItemBase):
    """Write DTO for creating a purchase order item"""
    pass


class CreatePurchaseOrderWriteDto(PurchaseOrderBase):
    """Write DTO for creating a purchase order with items"""
    items: Optional[List[CreatePurchaseOrderItemWriteDto]] = Field(default=None, description="Optional list of purchase order items")


class CreatePurchaseOrderControllerWriteDto(CreatePurchaseOrderWriteDto):
    """Controller DTO for creating a purchase order"""
    pass


class CreatePurchaseOrderServiceWriteDto(CreatePurchaseOrderWriteDto):
    """Service DTO for creating a purchase order"""
    pass


# =====================================================
# UPDATE PURCHASE ORDER WRITE DTOs
# =====================================================

class UpdatePurchaseOrderWriteBase(BaseModel):
    """Base write DTO for updating a purchase order"""
    supplier_id: Optional[str] = None
    assign_to: Optional[str] = None
    status: Optional[PurchaseOrderStatusType] = None
    order_date: Optional[date] = None
    expected_delivery_date: Optional[date] = None
    notes: Optional[str] = None


class UpdatePurchaseOrderItemWriteDto(BaseModel):
    """Write DTO for updating a purchase order item"""
    item_id: Optional[str] = Field(None, description="Item ID to update (if updating existing)")
    product_id: Optional[str] = None
    qty_ordered: Optional[int] = Field(None, gt=0)
    currency_id: Optional[str] = None
    cost_price: Optional[float] = Field(None, ge=0)
    base_selling_price: Optional[float] = Field(None, ge=0)


class UpdatePurchaseOrderWriteDto(UpdatePurchaseOrderWriteBase):
    """Write DTO for updating a purchase order with items"""
    items: Optional[List[UpdatePurchaseOrderItemWriteDto]] = Field(default=None, description="Optional list of purchase order items to update/create")


class UpdatePurchaseOrderControllerWriteDto(UpdatePurchaseOrderWriteDto):
    """Controller DTO for updating a purchase order"""
    pass


class UpdatePurchaseOrderServiceWriteDto(UpdatePurchaseOrderWriteDto):
    """Service DTO for updating a purchase order"""
    pass


# =====================================================
# CANCEL PURCHASE ORDER WRITE DTOs
# =====================================================

class CancelPurchaseOrderWriteBase(BaseModel):
    """Base write DTO for cancelling a purchase order"""
    purchase_order_id: str


class CancelPurchaseOrderControllerWriteDto(CancelPurchaseOrderWriteBase):
    """Controller DTO for cancelling a purchase order"""
    pass


class CancelPurchaseOrderServiceWriteDto(CancelPurchaseOrderWriteBase):
    """Service DTO for cancelling a purchase order"""
    pass


# =====================================================
# PERMANENT DELETE PURCHASE ORDER WRITE DTOs
# =====================================================

class PermanentDeletePurchaseOrderWriteBase(BaseModel):
    """Base write DTO for permanently deleting a purchase order"""
    purchase_order_id: str


class PermanentDeletePurchaseOrderControllerWriteDto(PermanentDeletePurchaseOrderWriteBase):
    """Controller DTO for permanently deleting a purchase order"""
    pass


class PermanentDeletePurchaseOrderServiceWriteDto(PermanentDeletePurchaseOrderWriteBase):
    """Service DTO for permanently deleting a purchase order"""
    pass


# =====================================================
# RECEIVE PURCHASE ORDER WRITE DTOs
# =====================================================

class ReceivePurchaseOrderItemWriteDto(PurchaseReceiptItemBase):
    """Write DTO for receiving a purchase order item"""
    pass


class ReceivePurchaseOrderWriteDto(PurchaseReceiptBase):
    """Write DTO for receiving a purchase order"""
    pass


class ReceivePurchaseOrderControllerWriteDto(ReceivePurchaseOrderWriteDto):
    """Controller DTO for receiving a purchase order"""
    pass


class ReceivePurchaseOrderServiceWriteDto(ReceivePurchaseOrderWriteDto):
    """Service DTO for receiving a purchase order"""
    pass


# =====================================================
# UPDATE PURCHASE RECEIPT WRITE DTOs
# =====================================================

class UpdatePurchaseReceiptWriteBase(BaseModel):
    """Base write DTO for updating a purchase receipt"""
    received_date: Optional[date] = None
    description: Optional[str] = None
    status: Optional[str] = None


class UpdatePurchaseReceiptControllerWriteDto(UpdatePurchaseReceiptWriteBase):
    """Controller DTO for updating a purchase receipt"""
    pass


class UpdatePurchaseReceiptServiceWriteDto(UpdatePurchaseReceiptWriteBase):
    """Service DTO for updating a purchase receipt"""
    pass


# =====================================================
# DELETE PURCHASE RECEIPT WRITE DTOs
# =====================================================

class DeletePurchaseReceiptWriteBase(BaseModel):
    """Base write DTO for deleting a purchase receipt"""
    receipt_id: str


class DeletePurchaseReceiptControllerWriteDto(DeletePurchaseReceiptWriteBase):
    """Controller DTO for deleting a purchase receipt"""
    pass


class DeletePurchaseReceiptServiceWriteDto(DeletePurchaseReceiptWriteBase):
    """Service DTO for deleting a purchase receipt"""
    pass
