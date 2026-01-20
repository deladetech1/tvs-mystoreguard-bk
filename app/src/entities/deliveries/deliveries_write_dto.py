from typing import Optional, List
from pydantic import BaseModel, Field
from src.entities.deliveries.deliveries_base import (
    DeliveryBase,
    DeliveryItemBase,
)


# =====================================================
# CREATE DELIVERY WRITE DTOs
# =====================================================

class CreateDeliveryWriteBase(BaseModel):
    """Base write DTO for creating a delivery"""
    sale_id: str = Field(..., description="Sale ID to deliver")
    delivery_type: str = Field(..., description="Delivery type: INTERNAL, THIRD_PARTY, or CUSTOMER_PICKUP")
    scheduled_date: Optional[str] = Field(None, description="Scheduled delivery date (YYYY-MM-DD)")
    delivery_fee: float = Field(default=0, ge=0, description="Delivery fee")
    currency_id: Optional[str] = Field(None, description="Currency ID")
    is_paid: bool = Field(default=False, description="Whether delivery fee is paid")
    recipient_name: str = Field(..., description="Recipient name")
    recipient_phone: Optional[str] = Field(None, description="Recipient phone number")
    delivery_address: str = Field(..., description="Delivery address")
    delivery_notes: Optional[str] = Field(None, description="Delivery notes")
    driver_id: Optional[str] = Field(None, description="Internal driver ID (for INTERNAL delivery type)")
    third_party_name: Optional[str] = Field(None, description="Third party name (e.g., DHL, Bolt) for THIRD_PARTY delivery type")
    tracking_number: Optional[str] = Field(None, description="Tracking number for third party deliveries")
    items: List[DeliveryItemBase] = Field(..., min_items=1, description="List of delivery items")


class CreateDeliveryControllerWriteDto(CreateDeliveryWriteBase):
    """Controller DTO for creating a delivery"""
    pass


class CreateDeliveryServiceWriteDto(CreateDeliveryWriteBase):
    """Service DTO for creating a delivery"""
    pass


# =====================================================
# UPDATE DELIVERY WRITE DTOs
# =====================================================

class UpdateDeliveryWriteBase(BaseModel):
    """Base write DTO for updating a delivery"""
    delivery_status: Optional[str] = Field(None, description="Delivery status")
    delivery_type: Optional[str] = Field(None, description="Delivery type")
    scheduled_date: Optional[str] = Field(None, description="Scheduled delivery date (YYYY-MM-DD)")
    delivery_fee: Optional[float] = Field(None, ge=0, description="Delivery fee")
    currency_id: Optional[str] = Field(None, description="Currency ID")
    is_paid: Optional[bool] = Field(None, description="Whether delivery fee is paid")
    recipient_name: Optional[str] = Field(None, description="Recipient name")
    recipient_phone: Optional[str] = Field(None, description="Recipient phone number")
    delivery_address: Optional[str] = Field(None, description="Delivery address")
    delivery_notes: Optional[str] = Field(None, description="Delivery notes")
    driver_id: Optional[str] = Field(None, description="Internal driver ID")
    third_party_name: Optional[str] = Field(None, description="Third party name")
    tracking_number: Optional[str] = Field(None, description="Tracking number")
    items: Optional[List[DeliveryItemBase]] = Field(None, description="Optional list of delivery items to update (replaces existing items)")


class UpdateDeliveryControllerWriteDto(UpdateDeliveryWriteBase):
    """Controller DTO for updating a delivery"""
    pass


class UpdateDeliveryServiceWriteDto(UpdateDeliveryWriteBase):
    """Service DTO for updating a delivery"""
    pass


# =====================================================
# UPDATE DELIVERY STATUS WRITE DTOs
# =====================================================

class UpdateDeliveryStatusWriteBase(BaseModel):
    """Base write DTO for updating delivery status"""
    delivery_id: str = Field(..., description="Delivery ID")
    delivery_status: str = Field(..., description="New delivery status")
    notes: Optional[str] = Field(None, description="Optional notes for status change")


class UpdateDeliveryStatusControllerWriteDto(UpdateDeliveryStatusWriteBase):
    """Controller DTO for updating delivery status"""
    pass


class UpdateDeliveryStatusServiceWriteDto(UpdateDeliveryStatusWriteBase):
    """Service DTO for updating delivery status"""
    pass


# =====================================================
# DISPATCH DELIVERY WRITE DTOs
# =====================================================

class DispatchDeliveryWriteBase(BaseModel):
    """Base write DTO for dispatching a delivery"""
    delivery_id: str = Field(..., description="Delivery ID")
    driver_id: Optional[str] = Field(None, description="Driver ID (for INTERNAL delivery type)")
    tracking_number: Optional[str] = Field(None, description="Tracking number (for THIRD_PARTY delivery type)")
    notes: Optional[str] = Field(None, description="Dispatch notes")


class DispatchDeliveryControllerWriteDto(DispatchDeliveryWriteBase):
    """Controller DTO for dispatching a delivery"""
    pass


class DispatchDeliveryServiceWriteDto(DispatchDeliveryWriteBase):
    """Service DTO for dispatching a delivery"""
    pass


# =====================================================
# COMPLETE DELIVERY WRITE DTOs
# =====================================================

class CompleteDeliveryWriteBase(BaseModel):
    """Base write DTO for completing a delivery"""
    delivery_id: str = Field(..., description="Delivery ID")
    notes: Optional[str] = Field(None, description="Completion notes")


class CompleteDeliveryControllerWriteDto(CompleteDeliveryWriteBase):
    """Controller DTO for completing a delivery"""
    pass


class CompleteDeliveryServiceWriteDto(CompleteDeliveryWriteBase):
    """Service DTO for completing a delivery"""
    pass


# =====================================================
# CANCEL DELIVERY WRITE DTOs
# =====================================================

class CancelDeliveryWriteBase(BaseModel):
    """Base write DTO for cancelling a delivery"""
    delivery_id: str = Field(..., description="Delivery ID")
    reason: Optional[str] = Field(None, description="Cancellation reason")


class CancelDeliveryControllerWriteDto(CancelDeliveryWriteBase):
    """Controller DTO for cancelling a delivery"""
    pass


class CancelDeliveryServiceWriteDto(CancelDeliveryWriteBase):
    """Service DTO for cancelling a delivery"""
    pass


# =====================================================
# DELETE DELIVERY WRITE DTOs
# =====================================================

class DeleteDeliveryWriteBase(BaseModel):
    """Base write DTO for deleting a delivery"""
    delivery_id: str = Field(..., description="Delivery ID")


class DeleteDeliveryControllerWriteDto(DeleteDeliveryWriteBase):
    """Controller DTO for deleting a delivery"""
    pass


class DeleteDeliveryServiceWriteDto(DeleteDeliveryWriteBase):
    """Service DTO for deleting a delivery"""
    pass

