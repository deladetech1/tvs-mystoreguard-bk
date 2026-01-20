from typing import Optional, List
from datetime import datetime, date
from decimal import Decimal
from pydantic import BaseModel, Field
from src.entities.promo_codes.promo_codes_base import (
    PromoCodeBase,
)


# =====================================================
# PROMO CODE READ DTOs
# =====================================================

class ApplicableProductItem(BaseModel):
    """Product item with ID and name"""
    product_id: str = Field(..., description="Product ID")
    product_name: str = Field(..., description="Product name")


class ApplicableProductMetadataItem(BaseModel):
    """Product metadata item with ID, name, and type"""
    metadata_id: str = Field(..., description="Metadata ID")
    metadata_name: str = Field(..., description="Metadata name")
    metadata_type: str = Field(..., description="Metadata type (CATEGORY, BRAND, TAG, LABEL)")


class ApplicableLocationItem(BaseModel):
    """Location item with ID and name"""
    location_id: str = Field(..., description="Location ID")
    location_name: str = Field(..., description="Location name")


class PromoCodeReadBase(PromoCodeBase):
    """Base read DTO for promo code"""
    id: str
    tenant_id: str
    org_id: str
    bus_id: str
    current_usage_count: int
    delete_status: str
    cdate: str
    ctime: str
    cdatetime: datetime
    created_by: Optional[str] = None
    updated_by: Optional[str] = None
    deleted_by: Optional[str] = None
    # Currency fields
    currency_name: Optional[str] = None
    currency_symbol: Optional[str] = None
    # Override applicable_to_products, applicable_to_product_metadata, and applicable_to_locations to be objects with names
    applicable_to_products: Optional[List[ApplicableProductItem]] = Field(None, description="List of products with IDs and names")
    applicable_to_product_metadata: Optional[List[ApplicableProductMetadataItem]] = Field(None, description="List of product metadata (categories, brands, tags, labels) with IDs, names, and types")
    applicable_to_locations: Optional[List[ApplicableLocationItem]] = Field(None, description="List of locations with IDs and names")


class CreatePromoCodeControllerReadDto(PromoCodeReadBase):
    """Controller DTO for create promo code read operations"""
    pass


class CreatePromoCodeServiceReadDto(PromoCodeReadBase):
    """Service DTO for create promo code read operations"""
    pass


class UpdatePromoCodeControllerReadDto(PromoCodeReadBase):
    """Controller DTO for update promo code read operations"""
    pass


class UpdatePromoCodeServiceReadDto(PromoCodeReadBase):
    """Service DTO for update promo code read operations"""
    pass


class GetPromoCodeControllerReadDto(PromoCodeReadBase):
    """Controller DTO for get promo code read operations"""
    pass


class GetPromoCodeServiceReadDto(PromoCodeReadBase):
    """Service DTO for get promo code read operations"""
    pass


class GetPromoCodesControllerReadDto(PromoCodeReadBase):
    """Controller DTO for get promo codes read operations"""
    pass


class GetPromoCodesServiceReadDto(PromoCodeReadBase):
    """Service DTO for get promo codes read operations"""
    pass


class DeletePromoCodeReadBase(BaseModel):
    """Base read DTO for delete promo code result"""
    promo_code_id: str
    message: str


class DeletePromoCodeControllerReadDto(DeletePromoCodeReadBase):
    """Controller DTO for delete promo code read operations"""
    pass


class DeletePromoCodeServiceReadDto(DeletePromoCodeReadBase):
    """Service DTO for delete promo code read operations"""
    pass


# =====================================================
# PROMO CODE STATISTICS READ DTOs
# =====================================================

class PromoCodesStatisticsReadDto(BaseModel):
    """Promo codes statistics DTO"""
    total_promo_codes: int = Field(default=0, description="Total number of promo codes")
    total_active: int = Field(default=0, description="Total active promo codes")
    total_inactive: int = Field(default=0, description="Total inactive promo codes")
    total_expired: int = Field(default=0, description="Total expired promo codes")
    total_usage_count: int = Field(default=0, description="Total usage count across all promo codes")
    total_discount_given: float = Field(default=0, description="Total discount amount given")
    average_discount_per_usage: float = Field(default=0, description="Average discount per usage")
    total_sales_using_promo_codes: int = Field(default=0, description="Total number of sales using promo codes")


class GetPromoCodesStatisticsControllerReadDto(PromoCodesStatisticsReadDto):
    """Controller DTO for promo codes statistics"""
    pass


class GetPromoCodesStatisticsServiceReadDto(PromoCodesStatisticsReadDto):
    """Service DTO for promo codes statistics"""
    pass

