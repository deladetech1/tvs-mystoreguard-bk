from typing import Optional, List
from datetime import datetime
from decimal import Decimal
from pydantic import BaseModel, Field
from src.entities.affiliates.affiliates_base import (
    AffiliateBase,
)


# =====================================================
# AFFILIATE READ DTOs
# =====================================================

class ApplicableLocationItem(BaseModel):
    """Location item with ID and name"""
    location_id: str = Field(..., description="Location ID")
    location_name: str = Field(..., description="Location name")


class ApplicableProductItem(BaseModel):
    """Product item with ID and name"""
    product_id: str = Field(..., description="Product ID")
    product_name: str = Field(..., description="Product name")


class ApplicableProductMetadataItem(BaseModel):
    """Product metadata item with ID, name, and type"""
    metadata_id: str = Field(..., description="Product metadata ID")
    metadata_name: str = Field(..., description="Product metadata name")
    metadata_type: str = Field(..., description="Product metadata type (CATEGORY, BRAND, TAG, LABEL, etc.)")


class AffiliateReadBase(AffiliateBase):
    """Base read DTO for affiliate"""
    id: str
    tenant_id: str
    org_id: str
    bus_id: str
    total_referrals: int
    total_conversions: int
    total_commission_earned: Decimal
    total_commission_paid: Decimal
    delete_status: str
    cdate: str
    ctime: str
    cdatetime: datetime
    created_by: Optional[str] = None
    updated_by: Optional[str] = None
    deleted_by: Optional[str] = None
    # Override applicable fields to be objects with names
    applicable_to_locations: Optional[List[ApplicableLocationItem]] = Field(None, description="List of locations with IDs and names")
    applicable_to_products: Optional[List[ApplicableProductItem]] = Field(None, description="List of products with IDs and names")
    applicable_to_product_metadata: Optional[List[ApplicableProductMetadataItem]] = Field(None, description="List of product metadata with IDs, names, and types")


class CreateAffiliateControllerReadDto(AffiliateReadBase):
    """Controller DTO for create affiliate read operations"""
    pass


class CreateAffiliateServiceReadDto(AffiliateReadBase):
    """Service DTO for create affiliate read operations"""
    pass


class UpdateAffiliateControllerReadDto(AffiliateReadBase):
    """Controller DTO for update affiliate read operations"""
    pass


class UpdateAffiliateServiceReadDto(AffiliateReadBase):
    """Service DTO for update affiliate read operations"""
    pass


class GetAffiliateControllerReadDto(AffiliateReadBase):
    """Controller DTO for get affiliate read operations"""
    pass


class GetAffiliateServiceReadDto(AffiliateReadBase):
    """Service DTO for get affiliate read operations"""
    pass


class GetAffiliatesControllerReadDto(AffiliateReadBase):
    """Controller DTO for get affiliates read operations"""
    pass


class GetAffiliatesServiceReadDto(AffiliateReadBase):
    """Service DTO for get affiliates read operations"""
    pass


class DeleteAffiliateReadBase(BaseModel):
    """Base read DTO for delete affiliate result"""
    affiliate_id: str
    message: str


class DeleteAffiliateControllerReadDto(DeleteAffiliateReadBase):
    """Controller DTO for delete affiliate read operations"""
    pass


class DeleteAffiliateServiceReadDto(DeleteAffiliateReadBase):
    """Service DTO for delete affiliate read operations"""
    pass


# =====================================================
# AFFILIATE STATISTICS READ DTOs
# =====================================================

class AffiliatesStatisticsReadDto(BaseModel):
    """Affiliates statistics DTO"""
    total_affiliates: int = Field(default=0, description="Total number of affiliates")
    total_active: int = Field(default=0, description="Total active affiliates")
    total_inactive: int = Field(default=0, description="Total inactive affiliates")
    total_referrals: int = Field(default=0, description="Total referrals across all affiliates")
    total_conversions: int = Field(default=0, description="Total conversions across all affiliates")
    total_commission_earned: float = Field(default=0, description="Total commission earned")
    total_commission_paid: float = Field(default=0, description="Total commission paid")
    total_pending_commission: float = Field(default=0, description="Total pending commission (earned - paid)")


class GetAffiliatesStatisticsControllerReadDto(AffiliatesStatisticsReadDto):
    """Controller DTO for affiliates statistics"""
    pass


class GetAffiliatesStatisticsServiceReadDto(AffiliatesStatisticsReadDto):
    """Service DTO for affiliates statistics"""
    pass

