from typing import Optional
from datetime import datetime
from pydantic import BaseModel, Field
from src.entities.prod_metadata.prod_metadata_base import (
    ProductMetadataBase,
    ProductMetadataType,
)


# =====================================================
# PRODUCT METADATA READ DTOs
# =====================================================

class ProductMetadataReadBase(ProductMetadataBase):
    """Base read DTO for product metadata"""
    id: str
    tenant_id: str
    org_id: str
    bus_id: str
    delete_status: str
    is_active: bool
    cdate: Optional[str] = None
    ctime: Optional[str] = None
    cdatetime: Optional[datetime] = None
    created_by: Optional[str] = None
    updated_by: Optional[str] = None
    deleted_by: Optional[str] = None


class CreateProductMetadataControllerReadDto(ProductMetadataReadBase):
    """Controller DTO for create product metadata read operations"""
    pass


class CreateProductMetadataServiceReadDto(ProductMetadataReadBase):
    """Service DTO for create product metadata read operations"""
    pass


class UpdateProductMetadataControllerReadDto(ProductMetadataReadBase):
    """Controller DTO for update product metadata read operations"""
    pass


class UpdateProductMetadataServiceReadDto(ProductMetadataReadBase):
    """Service DTO for update product metadata read operations"""
    pass


class GetProductMetadataControllerReadDto(ProductMetadataReadBase):
    """Controller DTO for get product metadata read operations"""
    pass


class GetProductMetadataServiceReadDto(ProductMetadataReadBase):
    """Service DTO for get product metadata read operations"""
    pass


class GetProductMetadataListControllerReadDto(ProductMetadataReadBase):
    """Controller DTO for get product metadata list read operations"""
    pass


class GetProductMetadataListServiceReadDto(ProductMetadataReadBase):
    """Service DTO for get product metadata list read operations"""
    pass


class DeleteProductMetadataReadBase(BaseModel):
    """Base read DTO for delete product metadata result"""
    metadata_id: str
    message: str


class DeleteProductMetadataControllerReadDto(DeleteProductMetadataReadBase):
    """Controller DTO for delete product metadata read operations"""
    pass


class DeleteProductMetadataServiceReadDto(DeleteProductMetadataReadBase):
    """Service DTO for delete product metadata read operations"""
    pass


# =====================================================
# PRODUCT METADATA STATISTICS READ DTOs
# =====================================================

class ProductMetadataStatisticsReadBase(BaseModel):
    """Base read DTO for product metadata statistics"""
    total_tags: int = Field(default=0, description="Total number of tags")
    total_categories: int = Field(default=0, description="Total number of categories")
    total_labels: int = Field(default=0, description="Total number of labels")
    total_brands: int = Field(default=0, description="Total number of brands")


class GetProductMetadataStatisticsControllerReadDto(ProductMetadataStatisticsReadBase):
    """Controller DTO for product metadata statistics"""
    pass


class GetProductMetadataStatisticsServiceReadDto(ProductMetadataStatisticsReadBase):
    """Service DTO for product metadata statistics"""
    pass

