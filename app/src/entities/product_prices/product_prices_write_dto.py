from typing import Optional
from decimal import Decimal
from pydantic import BaseModel, Field
from src.entities.product_prices.product_prices_base import ProductPriceBase


# =====================================================
# CREATE PRODUCT PRICE WRITE DTOs
# =====================================================

class CreateProductPriceWriteBase(ProductPriceBase):
    """Base write DTO for creating a product price"""
    pass


class CreateProductPriceControllerWriteDto(CreateProductPriceWriteBase):
    """Controller DTO for creating a product price"""
    pass


class CreateProductPriceServiceWriteDto(CreateProductPriceWriteBase):
    """Service DTO for creating a product price"""
    pass


# =====================================================
# UPDATE PRODUCT PRICE WRITE DTOs
# =====================================================

class UpdateProductPriceWriteBase(BaseModel):
    """Base write DTO for updating a product price"""
    product_id: Optional[str] = Field(None, description="ID of the product")
    of_type: Optional[str] = Field(None, description="Type of price: SKU, GLOBAL, LOCATION, TAG, CATEGORY, BRAND, or LABEL")
    target_id: Optional[str] = Field(None, description="ID of the target (location.id or product_metadata.id)")
    price: Optional[Decimal] = Field(None, decimal_places=2, ge=0, description="Price value (must be >= 0)")
    currency: Optional[str] = Field(None, min_length=1, description="Currency ID")
    priority: Optional[int] = Field(None, ge=0, description="Priority for price matching (higher priority takes precedence)")
    stops_other_prices: Optional[bool] = Field(None, description="If true, this price stops/overrides other prices and becomes the fixed price")


class UpdateProductPriceControllerWriteDto(UpdateProductPriceWriteBase):
    """Controller DTO for updating a product price"""
    pass


class UpdateProductPriceServiceWriteDto(UpdateProductPriceWriteBase):
    """Service DTO for updating a product price"""
    pass


# =====================================================
# DELETE PRODUCT PRICE WRITE DTOs
# =====================================================

class DeleteProductPriceWriteBase(BaseModel):
    """Base write DTO for deleting a product price"""
    price_id: str = Field(..., description="ID of the price to delete")


class DeleteProductPriceControllerWriteDto(DeleteProductPriceWriteBase):
    """Controller DTO for deleting a product price"""
    pass


class DeleteProductPriceServiceWriteDto(DeleteProductPriceWriteBase):
    """Service DTO for deleting a product price"""
    pass

