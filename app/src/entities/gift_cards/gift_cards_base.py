from typing import Optional, List
from typing_extensions import Literal
from pydantic import BaseModel, Field
from datetime import date
from decimal import Decimal


# =====================================================
# ENUMS AND LITERALS
# =====================================================

GiftCardStatusType = Literal['ACTIVE', 'USED', 'EXPIRED', 'CANCELLED']
DeleteStatusType = Literal['PENDING', 'DELETED', 'NOT_DELETED']
GiftCardTransactionType = Literal['PURCHASE', 'REDEMPTION', 'REFUND', 'ADJUSTMENT', 'EXPIRY']


# =====================================================
# GIFT CARD BASE DTOs
# =====================================================

class GiftCardBase(BaseModel):
    """Base DTO for gift card information"""
    gift_card_code: str = Field(..., min_length=1, description="Unique gift card code")
    initial_value: Decimal = Field(..., gt=0, decimal_places=2, description="Initial value of the gift card")
    current_balance: Optional[Decimal] = Field(None, ge=0, decimal_places=2, description="Current balance (will be set to initial_value if not provided)")
    currency_id: str = Field(..., description="Currency ID for the gift card")
    status: GiftCardStatusType = Field(default='ACTIVE', description="Gift card status")
    expiry_date: Optional[date] = Field(None, description="Expiry date (optional)")
    purchase_date: Optional[date] = Field(None, description="Purchase date (defaults to current date)")
    purchased_by_customer_id: Optional[str] = Field(None, description="Customer who purchased the gift card (optional)")
    description: Optional[str] = Field(None, description="Description")
    notes: Optional[str] = Field(None, description="Additional notes")
    applicable_to_locations: Optional[List[str]] = Field(None, description="List of location IDs where this gift card can be used. If empty/null, applies to all locations")
    is_active: bool = Field(default=True, description="Whether the gift card is active")


class GiftCardWriteBase(BaseModel):
    """Base DTO for gift card write operations (without current_balance - it's set automatically from initial_value)"""
    gift_card_code: str = Field(..., min_length=1, description="Unique gift card code")
    initial_value: Decimal = Field(..., gt=0, decimal_places=2, description="Initial value of the gift card")
    currency_id: str = Field(..., description="Currency ID for the gift card")
    status: GiftCardStatusType = Field(default='ACTIVE', description="Gift card status")
    expiry_date: Optional[date] = Field(None, description="Expiry date (optional)")
    purchase_date: Optional[date] = Field(None, description="Purchase date (defaults to current date)")
    purchased_by_customer_id: Optional[str] = Field(None, description="Customer who purchased the gift card (optional)")
    description: Optional[str] = Field(None, description="Description")
    notes: Optional[str] = Field(None, description="Additional notes")
    applicable_to_locations: Optional[List[str]] = Field(None, description="List of location IDs where this gift card can be used. If empty/null, applies to all locations")
    is_active: bool = Field(default=True, description="Whether the gift card is active")

