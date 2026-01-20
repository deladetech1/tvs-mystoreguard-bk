from typing import Optional
from typing_extensions import Literal
from pydantic import BaseModel, Field
from datetime import date
from decimal import Decimal


# =====================================================
# ENUMS AND LITERALS
# =====================================================

DeliveryStatusType = Literal[
    'PENDING',
    'SCHEDULED',
    'OUT_FOR_DELIVERY',
    'DELIVERED',
    'FAILED',
    'CANCELLED'
]

DeliveryTypeType = Literal[
    'INTERNAL',
    'THIRD_PARTY',
    'CUSTOMER_PICKUP'
]


# =====================================================
# DELIVERY BASE DTOs
# =====================================================

class DeliveryBase(BaseModel):
    """Base DTO for delivery information"""
    sale_id: str = Field(..., description="Sale ID to deliver")
    delivery_status: DeliveryStatusType = Field(default='PENDING', description="Delivery status")
    delivery_type: DeliveryTypeType = Field(..., description="Delivery type: INTERNAL, THIRD_PARTY, or CUSTOMER_PICKUP")
    scheduled_date: Optional[date] = Field(None, description="Scheduled delivery date")
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


# =====================================================
# DELIVERY ITEM BASE DTOs
# =====================================================

class DeliveryItemBase(BaseModel):
    """Base DTO for delivery item information"""
    sale_item_id: str = Field(..., description="Sale item ID to deliver")
    product_id: str = Field(..., description="Product ID")
    ordered_qty: float = Field(..., gt=0, description="Ordered quantity (must be greater than 0)")
    delivered_qty: float = Field(..., gt=0, description="Delivered quantity (must be greater than 0)")

