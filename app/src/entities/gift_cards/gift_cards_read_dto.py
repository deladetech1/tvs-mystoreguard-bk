from typing import Optional, List
from datetime import datetime, date
from decimal import Decimal
from pydantic import BaseModel, Field
from src.entities.gift_cards.gift_cards_base import (
    GiftCardBase,
)


# =====================================================
# GIFT CARD READ DTOs
# =====================================================

class ApplicableLocationItem(BaseModel):
    """Location item with ID and name"""
    location_id: str = Field(..., description="Location ID")
    location_name: str = Field(..., description="Location name")


class GiftCardReadBase(GiftCardBase):
    """Base read DTO for gift card"""
    id: str
    tenant_id: str
    org_id: str
    bus_id: str
    delete_status: str
    purchased_by_user_id: Optional[str] = None
    cdate: str
    ctime: str
    cdatetime: datetime
    created_by: Optional[str] = None
    updated_by: Optional[str] = None
    deleted_by: Optional[str] = None
    # Currency fields
    currency_name: Optional[str] = None
    currency_symbol: Optional[str] = None
    # Customer fields
    purchased_by_customer_fullname: Optional[str] = None
    # Override applicable_to_locations to be objects with names
    applicable_to_locations: Optional[List[ApplicableLocationItem]] = Field(None, description="List of locations with IDs and names")


class CreateGiftCardControllerReadDto(GiftCardReadBase):
    """Controller DTO for create gift card read operations"""
    pass


class CreateGiftCardServiceReadDto(GiftCardReadBase):
    """Service DTO for create gift card read operations"""
    pass


class UpdateGiftCardControllerReadDto(GiftCardReadBase):
    """Controller DTO for update gift card read operations"""
    pass


class UpdateGiftCardServiceReadDto(GiftCardReadBase):
    """Service DTO for update gift card read operations"""
    pass


class GetGiftCardControllerReadDto(GiftCardReadBase):
    """Controller DTO for get gift card read operations"""
    pass


class GetGiftCardServiceReadDto(GiftCardReadBase):
    """Service DTO for get gift card read operations"""
    pass


class GetGiftCardsControllerReadDto(GiftCardReadBase):
    """Controller DTO for get gift cards read operations"""
    pass


class GetGiftCardsServiceReadDto(GiftCardReadBase):
    """Service DTO for get gift cards read operations"""
    pass


class DeleteGiftCardReadBase(BaseModel):
    """Base read DTO for delete gift card result"""
    gift_card_id: str
    message: str


class DeleteGiftCardControllerReadDto(DeleteGiftCardReadBase):
    """Controller DTO for delete gift card read operations"""
    pass


class DeleteGiftCardServiceReadDto(DeleteGiftCardReadBase):
    """Service DTO for delete gift card read operations"""
    pass


# =====================================================
# GIFT CARD STATISTICS READ DTOs
# =====================================================

class GiftCardsStatisticsReadDto(BaseModel):
    """Gift cards statistics DTO"""
    total_gift_cards: int = Field(default=0, description="Total number of gift cards")
    total_active: int = Field(default=0, description="Total active gift cards")
    total_used: int = Field(default=0, description="Total used gift cards")
    total_expired: int = Field(default=0, description="Total expired gift cards")
    total_cancelled: int = Field(default=0, description="Total cancelled gift cards")
    total_initial_value: float = Field(default=0, description="Total initial value of all gift cards")
    total_current_balance: float = Field(default=0, description="Total current balance of all gift cards")
    total_redeemed_value: float = Field(default=0, description="Total redeemed value (initial - current balance)")


class GetGiftCardsStatisticsControllerReadDto(GiftCardsStatisticsReadDto):
    """Controller DTO for gift cards statistics"""
    pass


class GetGiftCardsStatisticsServiceReadDto(GiftCardsStatisticsReadDto):
    """Service DTO for gift cards statistics"""
    pass

