from typing import Optional
from pydantic import BaseModel, Field
from src.entities.prod_metadata.prod_metadata_base import (
    ProductMetadataBase,
    ProductMetadataType,
    DeleteStatusType,
)


# =====================================================
# CREATE PRODUCT METADATA WRITE DTOs
# =====================================================

class CreateProductMetadataWriteBase(ProductMetadataBase):
    """Base write DTO for creating product metadata"""
    pass


class CreateProductMetadataControllerWriteDto(CreateProductMetadataWriteBase):
    """Controller DTO for creating product metadata"""
    pass


class CreateProductMetadataServiceWriteDto(CreateProductMetadataWriteBase):
    """Service DTO for creating product metadata"""
    pass


# =====================================================
# UPDATE PRODUCT METADATA WRITE DTOs
# =====================================================

class UpdateProductMetadataWriteBase(BaseModel):
    """Base write DTO for updating product metadata"""
    name: Optional[str] = Field(None, min_length=1, max_length=255, description="Name of the metadata")
    description: Optional[str] = Field(None, max_length=1000, description="Optional description of the metadata")
    is_active: Optional[bool] = Field(None, description="Whether the metadata is active")


class UpdateProductMetadataControllerWriteDto(UpdateProductMetadataWriteBase):
    """Controller DTO for updating product metadata"""
    pass


class UpdateProductMetadataServiceWriteDto(UpdateProductMetadataWriteBase):
    """Service DTO for updating product metadata"""
    pass


# =====================================================
# DELETE PRODUCT METADATA WRITE DTOs
# =====================================================

class DeleteProductMetadataWriteBase(BaseModel):
    """Base write DTO for deleting product metadata"""
    metadata_id: str = Field(..., description="ID of the product metadata to delete")


class DeleteProductMetadataControllerWriteDto(DeleteProductMetadataWriteBase):
    """Controller DTO for deleting product metadata"""
    pass


class DeleteProductMetadataServiceWriteDto(DeleteProductMetadataWriteBase):
    """Service DTO for deleting product metadata"""
    pass

