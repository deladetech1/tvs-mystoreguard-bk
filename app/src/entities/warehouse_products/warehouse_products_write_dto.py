from typing import Optional, List
from pydantic import BaseModel, Field
from src.entities.warehouse_products.warehouse_products_base import (
    WarehouseProductBase,
    DeleteStatusType,
)


# =====================================================
# CREATE WAREHOUSE PRODUCT WRITE DTOs
# =====================================================

class CreateWarehouseProductWriteBase(WarehouseProductBase):
    """Base write DTO for creating a warehouse product"""
    pass


class CreateWarehouseProductControllerWriteDto(CreateWarehouseProductWriteBase):
    """Controller DTO for creating a warehouse product"""
    pass


class CreateWarehouseProductServiceWriteDto(CreateWarehouseProductWriteBase):
    """Service DTO for creating a warehouse product"""
    pass


# =====================================================
# UPDATE WAREHOUSE PRODUCT WRITE DTOs
# =====================================================

class UpdateWarehouseProductWriteBase(BaseModel):
    """Base write DTO for updating a warehouse product"""
    comment: Optional[str] = None
    reorder_level: Optional[int] = Field(None, ge=0)
    reorder_quantity: Optional[int] = Field(None, ge=0)
    is_active: Optional[bool] = None


class UpdateWarehouseProductControllerWriteDto(UpdateWarehouseProductWriteBase):
    """Controller DTO for updating a warehouse product"""
    pass


class UpdateWarehouseProductServiceWriteDto(UpdateWarehouseProductWriteBase):
    """Service DTO for updating a warehouse product"""
    pass


# =====================================================
# DELETE WAREHOUSE PRODUCT WRITE DTOs (Soft Delete)
# =====================================================

class DeleteWarehouseProductWriteBase(BaseModel):
    """Base write DTO for soft deleting a warehouse product"""
    loc_id: str
    product_id: str


class DeleteWarehouseProductControllerWriteDto(DeleteWarehouseProductWriteBase):
    """Controller DTO for soft deleting a warehouse product"""
    pass


class DeleteWarehouseProductServiceWriteDto(DeleteWarehouseProductWriteBase):
    """Service DTO for soft deleting a warehouse product"""
    pass


# =====================================================
# PERMANENT DELETE WAREHOUSE PRODUCT WRITE DTOs
# =====================================================

class PermanentDeleteWarehouseProductWriteBase(BaseModel):
    """Base write DTO for permanently deleting a warehouse product"""
    product_id: str


class PermanentDeleteWarehouseProductControllerWriteDto(PermanentDeleteWarehouseProductWriteBase):
    """Controller DTO for permanently deleting a warehouse product"""
    pass


class PermanentDeleteWarehouseProductServiceWriteDto(PermanentDeleteWarehouseProductWriteBase):
    """Service DTO for permanently deleting a warehouse product"""
    pass


# =====================================================
# REVERSE BATCH WAREHOUSE PRODUCT WRITE DTOs
# =====================================================

class ReverseBatchWarehouseProductWriteBase(BaseModel):
    """Base write DTO for reversing a batch allocation from a warehouse product"""
    loc_id: str = Field(..., description="Location ID")
    product_id: str = Field(..., description="Product ID")
    batch_number: str = Field(..., description="Batch number to reverse")


class ReverseBatchWarehouseProductControllerWriteDto(ReverseBatchWarehouseProductWriteBase):
    """Controller DTO for reversing a batch allocation from a warehouse product"""
    pass


class ReverseBatchWarehouseProductServiceWriteDto(ReverseBatchWarehouseProductWriteBase):
    """Service DTO for reversing a batch allocation from a warehouse product"""
    pass


# =====================================================
# ADD STOCK WAREHOUSE PRODUCT WRITE DTOs
# =====================================================

class AddStockWarehouseProductWriteBase(BaseModel):
    """Base write DTO for adding stock to an existing warehouse product"""
    product_id: str = Field(..., description="Product ID")
    qty: int = Field(..., gt=0, description="Quantity to add (must be greater than 0)")
    batch_numbers: Optional[List[str]] = Field(default=None, description="Optional list of batch numbers. If empty, batches will be selected automatically using FIFO")


class AddStockWarehouseProductControllerWriteDto(AddStockWarehouseProductWriteBase):
    """Controller DTO for adding stock to a warehouse product"""
    pass


class AddStockWarehouseProductServiceWriteDto(AddStockWarehouseProductWriteBase):
    """Service DTO for adding stock to a warehouse product"""
    pass

