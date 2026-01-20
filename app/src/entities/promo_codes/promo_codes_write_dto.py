from typing import Optional, List
from pydantic import BaseModel, Field
from decimal import Decimal
from datetime import date
from src.entities.promo_codes.promo_codes_base import (
    PromoCodeBase,
    DeleteStatusType,
)


# =====================================================
# CREATE PROMO CODE WRITE DTOs
# =====================================================

class CreatePromoCodeWriteBase(PromoCodeBase):
    """Base write DTO for creating a promo code"""
    pass


class CreatePromoCodeControllerWriteDto(CreatePromoCodeWriteBase):
    """Controller DTO for creating a promo code"""
    pass


class CreatePromoCodeServiceWriteDto(CreatePromoCodeWriteBase):
    """Service DTO for creating a promo code"""
    pass


# =====================================================
# UPDATE PROMO CODE WRITE DTOs
# =====================================================

class UpdatePromoCodeWriteBase(BaseModel):
    """Base write DTO for updating a promo code"""
    promo_code: Optional[str] = None
    discount_type: Optional[str] = None
    discount_value: Optional[Decimal] = None
    min_purchase_amount: Optional[Decimal] = None
    max_discount_amount: Optional[Decimal] = None
    usage_limit_per_customer: Optional[int] = None
    total_usage_limit: Optional[int] = None
    start_date: Optional[date] = None
    end_date: Optional[date] = None
    status: Optional[str] = None
    applicable_to_customers_only: Optional[bool] = None
    applicable_to_locations: Optional[List[str]] = None
    applicable_to_products: Optional[List[str]] = None
    applicable_to_product_metadata: Optional[List[str]] = None
    description: Optional[str] = None
    notes: Optional[str] = None
    is_active: Optional[bool] = None


class UpdatePromoCodeControllerWriteDto(UpdatePromoCodeWriteBase):
    """Controller DTO for updating a promo code"""
    pass


class UpdatePromoCodeServiceWriteDto(UpdatePromoCodeWriteBase):
    """Service DTO for updating a promo code"""
    pass


# =====================================================
# DELETE PROMO CODE WRITE DTOs
# =====================================================

class DeletePromoCodeWriteBase(BaseModel):
    """Base write DTO for deleting a promo code"""
    promo_code_id: str


class DeletePromoCodeControllerWriteDto(DeletePromoCodeWriteBase):
    """Controller DTO for deleting a promo code"""
    pass


class DeletePromoCodeServiceWriteDto(DeletePromoCodeWriteBase):
    """Service DTO for deleting a promo code"""
    pass

