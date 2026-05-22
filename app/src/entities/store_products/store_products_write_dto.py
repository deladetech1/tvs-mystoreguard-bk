from typing import Optional, List
from pydantic import BaseModel, Field
from src.entities.store_products.store_products_base import (
    StoreProductBase,
    DeleteStatusType,
)


# =====================================================
# CREATE STORE PRODUCT WRITE DTOs
# =====================================================

class CreateStoreProductWriteBase(StoreProductBase):
    """Base write DTO for creating a store product"""
    pass


class CreateStoreProductControllerWriteDto(CreateStoreProductWriteBase):
    """Controller DTO for creating a store product"""
    pass


class CreateStoreProductServiceWriteDto(CreateStoreProductWriteBase):
    """Service DTO for creating a store product"""
    pass


# =====================================================
# UPDATE STORE PRODUCT WRITE DTOs
# =====================================================

class UpdateStoreProductWriteBase(BaseModel):
    """Base write DTO for updating a store product"""
    description: Optional[str] = None
    reorder_level: Optional[int] = Field(None, ge=0)
    reorder_quantity: Optional[int] = Field(None, ge=0)
    is_active: Optional[bool] = None


class UpdateStoreProductControllerWriteDto(UpdateStoreProductWriteBase):
    """Controller DTO for updating a store product"""
    pass


class UpdateStoreProductServiceWriteDto(UpdateStoreProductWriteBase):
    """Service DTO for updating a store product"""
    pass


# =====================================================
# DELETE STORE PRODUCT WRITE DTOs (Soft Delete)
# =====================================================

class DeleteStoreProductWriteBase(BaseModel):
    """Base write DTO for soft deleting a store product"""
    loc_id: str
    product_id: str


class DeleteStoreProductControllerWriteDto(DeleteStoreProductWriteBase):
    """Controller DTO for soft deleting a store product"""
    pass


class DeleteStoreProductServiceWriteDto(DeleteStoreProductWriteBase):
    """Service DTO for soft deleting a store product"""
    pass


# =====================================================
# PERMANENT DELETE STORE PRODUCT WRITE DTOs
# =====================================================

class PermanentDeleteStoreProductWriteBase(BaseModel):
    """Base write DTO for permanently deleting a store product"""
    product_id: str


class PermanentDeleteStoreProductControllerWriteDto(PermanentDeleteStoreProductWriteBase):
    """Controller DTO for permanently deleting a store product"""
    pass


class PermanentDeleteStoreProductServiceWriteDto(PermanentDeleteStoreProductWriteBase):
    """Service DTO for permanently deleting a store product"""
    pass


# =====================================================
# REVERSE BATCH STORE PRODUCT WRITE DTOs
# =====================================================

class ReverseBatchStoreProductWriteBase(BaseModel):
    """Base write DTO for reversing a batch allocation from a store product"""
    product_id: str = Field(..., description="Product ID")
    batch_number: str = Field(..., description="Batch number to reverse")


class ReverseBatchStoreProductControllerWriteDto(ReverseBatchStoreProductWriteBase):
    """Controller DTO for reversing a batch allocation from a store product"""
    pass


class ReverseBatchStoreProductServiceWriteDto(ReverseBatchStoreProductWriteBase):
    """Service DTO for reversing a batch allocation from a store product"""
    pass


# =====================================================
# ADD STOCK STORE PRODUCT WRITE DTOs
# =====================================================

class AddStockStoreProductWriteBase(BaseModel):
    """Base write DTO for adding stock to an existing store product"""
    product_id: str = Field(..., description="Product ID")
    qty: int = Field(..., gt=0, description="Quantity to add (must be greater than 0)")
    batch_numbers: Optional[List[str]] = Field(default=None, description="Optional list of batch numbers. If empty, batches will be selected automatically using FIFO")


class AddStockStoreProductControllerWriteDto(AddStockStoreProductWriteBase):
    """Controller DTO for adding stock to a store product"""
    pass


class AddStockStoreProductServiceWriteDto(AddStockStoreProductWriteBase):
    """Service DTO for adding stock to a store product"""
    pass

