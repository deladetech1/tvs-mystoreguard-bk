from typing import Optional, List
from pydantic import BaseModel, Field
from src.entities.products.products_base import (
    ProductBase,
    PurchaseBatchBase,
    DeleteStatusType,
    BatchStatusType,
)


# =====================================================
# CREATE PRODUCT WRITE DTOs
# =====================================================

class CreateProductWriteBase(BaseModel):
    """Base write DTO for creating a product with flat structure"""
    name: Optional[str] = Field(None, description="Product name (optional)")
    sku: Optional[str] = Field(None, description="Product SKU")
    bar_code: Optional[str] = Field(None, description="Product barcode")
    description: Optional[str] = Field(None, description="Product description")
    metadata_ids: List[str] = Field(default_factory=list, description="List of metadata IDs")
    is_active: Optional[bool] = Field(True, description="Whether the product is active")
    # Batch-related fields (all optional - only required when qty > 0)
    supplier_id: Optional[str] = Field(None, description="Supplier ID (required if qty > 0)")
    currency_id: Optional[str] = Field(None, description="Currency ID (required if qty > 0)")
    unit_of_measure_id: Optional[str] = Field(None, description="Unit of measure ID")
    cost_price: Optional[float] = Field(None, ge=0, description="Cost price (required if qty > 0)")
    base_selling_price: Optional[float] = Field(None, ge=0, description="Base selling price (required if qty > 0)")
    qty: Optional[int] = Field(None, ge=0, description="Quantity (if >= 1, creates a purchase batch; if 0 or None, no batch created)")
    batch_number: Optional[str] = Field(None, description="Batch number (optional - if not provided, one will be generated automatically)")
    size: Optional[str] = Field(None, description="Product size")
    expire_date: Optional[str] = Field(None, description="Expire date as string (YYYY-MM-DD)")
    document_ids: List[str] = Field(default_factory=list, description="List of document IDs")


class CreateProductControllerWriteDto(CreateProductWriteBase):
    """Controller DTO for creating a product"""
    pass


class CreateProductServiceWriteDto(CreateProductWriteBase):
    """Service DTO for creating a product"""
    pass


# =====================================================
# UPDATE PRODUCT WRITE DTOs
# =====================================================

class UpdateProductWriteBase(BaseModel):
    """Base write DTO for updating a product with flat structure"""
    name: Optional[str] = Field(None, description="Product name")
    sku: Optional[str] = Field(None, description="Product SKU")
    bar_code: Optional[str] = Field(None, description="Product barcode")
    description: Optional[str] = Field(None, description="Product description")
    metadata_ids: Optional[List[str]] = Field(None, description="List of metadata IDs")
    is_active: Optional[bool] = Field(None, description="Whether the product is active")
    document_ids: Optional[List[str]] = Field(None, description="List of document IDs")


class UpdateProductControllerWriteDto(UpdateProductWriteBase):
    """Controller DTO for updating a product"""
    pass


class UpdateProductServiceWriteDto(UpdateProductWriteBase):
    """Service DTO for updating a product"""
    pass


# =====================================================
# DELETE PRODUCT WRITE DTOs
# =====================================================

class DeleteProductWriteBase(BaseModel):
    """Base write DTO for deleting a product"""
    product_id: str


class DeleteProductControllerWriteDto(DeleteProductWriteBase):
    """Controller DTO for deleting a product"""
    pass


class DeleteProductServiceWriteDto(DeleteProductWriteBase):
    """Service DTO for deleting a product"""
    pass


# =====================================================
# PERMANENT DELETE PRODUCT WRITE DTOs
# =====================================================

class PermanentDeleteProductWriteBase(BaseModel):
    """Base write DTO for permanently deleting a product"""
    product_id: str


class PermanentDeleteProductControllerWriteDto(PermanentDeleteProductWriteBase):
    """Controller DTO for permanently deleting a product"""
    pass


class PermanentDeleteProductServiceWriteDto(PermanentDeleteProductWriteBase):
    """Service DTO for permanently deleting a product"""
    pass


# =====================================================
# ADD BATCH TO PRODUCT WRITE DTOs
# =====================================================

class AddBatchToProductWriteBase(BaseModel):
    """Base write DTO for adding a batch to an existing product"""
    product_id: str = Field(..., description="Product ID")
    supplier_id: Optional[str] = Field(None, description="Supplier ID")
    currency_id: str = Field(..., description="Currency ID (required)")
    unit_of_measure_id: Optional[str] = Field(None, description="Unit of measure ID")
    cost_price: float = Field(..., ge=0, description="Cost price (required, >= 0)")
    base_selling_price: float = Field(..., ge=0, description="Base selling price (required, >= 0)")
    qty_received: int = Field(..., gt=0, description="Quantity received (required, > 0)")
    size: Optional[str] = Field(None, description="Product size")
    expire_date: Optional[str] = Field(None, description="Expire date as string (YYYY-MM-DD)")
    is_active: Optional[bool] = Field(True, description="Whether the batch is active")


class AddBatchToProductControllerWriteDto(AddBatchToProductWriteBase):
    """Controller DTO for adding a batch to an existing product"""
    pass


class AddBatchToProductServiceWriteDto(AddBatchToProductWriteBase):
    """Service DTO for adding a batch to an existing product"""
    pass


# =====================================================
# REVERSE BATCH WRITE DTOs
# =====================================================

class ReverseBatchWriteBase(BaseModel):
    """Base write DTO for reversing a batch"""
    batch_number: str = Field(..., description="Batch number to reverse")


class ReverseBatchControllerWriteDto(ReverseBatchWriteBase):
    """Controller DTO for reversing a batch"""
    pass


class ReverseBatchServiceWriteDto(ReverseBatchWriteBase):
    """Service DTO for reversing a batch"""
    pass


# =====================================================
# DELETE BATCH WRITE DTOs
# =====================================================

class DeleteBatchWriteBase(BaseModel):
    """Base write DTO for deleting a batch"""
    product_id: str = Field(..., description="Product ID")
    batch_id: str = Field(..., description="Batch ID to delete")


class DeleteBatchControllerWriteDto(DeleteBatchWriteBase):
    """Controller DTO for deleting a batch"""
    pass


class DeleteBatchServiceWriteDto(DeleteBatchWriteBase):
    """Service DTO for deleting a batch"""
    pass


# =====================================================
# DELETE MOVEMENT WRITE DTOs
# =====================================================

class DeleteMovementWriteBase(BaseModel):
    """Base write DTO for deleting a movement"""
    product_id: str = Field(..., description="Product ID")
    movement_id: str = Field(..., description="Movement ID to delete")


class DeleteMovementControllerWriteDto(DeleteMovementWriteBase):
    """Controller DTO for deleting a movement"""
    pass


class DeleteMovementServiceWriteDto(DeleteMovementWriteBase):
    """Service DTO for deleting a movement"""
    pass

