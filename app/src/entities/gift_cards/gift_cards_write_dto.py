from typing import Optional, List
from pydantic import BaseModel, Field
from decimal import Decimal
from datetime import date
from src.entities.gift_cards.gift_cards_base import (
    GiftCardWriteBase,
    DeleteStatusType,
)


# =====================================================
# CREATE GIFT CARD WRITE DTOs
# =====================================================

class CreateGiftCardWriteBase(GiftCardWriteBase):
    """Base write DTO for creating a gift card (current_balance is set automatically from initial_value)"""
    pass


class CreateGiftCardControllerWriteDto(CreateGiftCardWriteBase):
    """Controller DTO for creating a gift card"""
    pass


class CreateGiftCardServiceWriteDto(CreateGiftCardWriteBase):
    """Service DTO for creating a gift card"""
    pass


# =====================================================
# UPDATE GIFT CARD WRITE DTOs
# =====================================================

class UpdateGiftCardWriteBase(BaseModel):
    """Base write DTO for updating a gift card"""
    gift_card_code: Optional[str] = None
    status: Optional[str] = None
    expiry_date: Optional[date] = None
    description: Optional[str] = None
    notes: Optional[str] = None
    applicable_to_locations: Optional[List[str]] = None
    is_active: Optional[bool] = None


class UpdateGiftCardControllerWriteDto(UpdateGiftCardWriteBase):
    """Controller DTO for updating a gift card"""
    pass


class UpdateGiftCardServiceWriteDto(UpdateGiftCardWriteBase):
    """Service DTO for updating a gift card"""
    pass


# =====================================================
# DELETE GIFT CARD WRITE DTOs
# =====================================================

class DeleteGiftCardWriteBase(BaseModel):
    """Base write DTO for deleting a gift card"""
    gift_card_id: str


class DeleteGiftCardControllerWriteDto(DeleteGiftCardWriteBase):
    """Controller DTO for deleting a gift card"""
    pass


class DeleteGiftCardServiceWriteDto(DeleteGiftCardWriteBase):
    """Service DTO for deleting a gift card"""
    pass

