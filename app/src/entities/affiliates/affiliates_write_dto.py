from typing import Optional, List
from pydantic import BaseModel, Field
from decimal import Decimal
from src.entities.affiliates.affiliates_base import (
    AffiliateBase,
    DeleteStatusType,
)


# =====================================================
# CREATE AFFILIATE WRITE DTOs
# =====================================================

class CreateAffiliateWriteBase(AffiliateBase):
    """Base write DTO for creating an affiliate"""
    pass


class CreateAffiliateControllerWriteDto(CreateAffiliateWriteBase):
    """Controller DTO for creating an affiliate"""
    pass


class CreateAffiliateServiceWriteDto(CreateAffiliateWriteBase):
    """Service DTO for creating an affiliate"""
    pass


# =====================================================
# UPDATE AFFILIATE WRITE DTOs
# =====================================================

class UpdateAffiliateWriteBase(BaseModel):
    """Base write DTO for updating an affiliate"""
    affiliate_code: Optional[str] = None
    affiliate_name: Optional[str] = None
    contact_email: Optional[str] = None
    contact_phone: Optional[str] = None
    commission_rate: Optional[Decimal] = None
    commission_type: Optional[str] = None
    fixed_commission_amount: Optional[Decimal] = None
    status: Optional[str] = None
    description: Optional[str] = None
    notes: Optional[str] = None
    applicable_to_locations: Optional[List[str]] = None
    applicable_to_products: Optional[List[str]] = None
    applicable_to_product_metadata: Optional[List[str]] = None
    is_active: Optional[bool] = None


class UpdateAffiliateControllerWriteDto(UpdateAffiliateWriteBase):
    """Controller DTO for updating an affiliate"""
    pass


class UpdateAffiliateServiceWriteDto(UpdateAffiliateWriteBase):
    """Service DTO for updating an affiliate"""
    pass


# =====================================================
# DELETE AFFILIATE WRITE DTOs
# =====================================================

class DeleteAffiliateWriteBase(BaseModel):
    """Base write DTO for deleting an affiliate"""
    affiliate_id: str


class DeleteAffiliateControllerWriteDto(DeleteAffiliateWriteBase):
    """Controller DTO for deleting an affiliate"""
    pass


class DeleteAffiliateServiceWriteDto(DeleteAffiliateWriteBase):
    """Service DTO for deleting an affiliate"""
    pass

