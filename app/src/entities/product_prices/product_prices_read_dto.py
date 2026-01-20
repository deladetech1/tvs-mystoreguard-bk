from typing import Optional
from datetime import datetime
from decimal import Decimal
from pydantic import BaseModel, Field
from src.entities.product_prices.product_prices_base import ProductPriceBase


# =====================================================
# PRODUCT PRICE READ DTOs
# =====================================================

class ProductPriceReadBase(ProductPriceBase):
    """Base read DTO for product price"""
    id: str
    tenant_id: str
    org_id: str
    bus_id: str
    target_name: Optional[str] = Field(None, description="Name of the target (e.g., location name, metadata name)")
    # Override currency to return symbol instead of ID
    currency: str = Field(..., description="Currency symbol (not the ID)")
    cdate: Optional[str] = None
    ctime: Optional[str] = None
    cdatetime: Optional[datetime] = None
    created_by: Optional[str] = None
    updated_by: Optional[str] = None
    deleted_by: Optional[str] = None


class CreateProductPriceControllerReadDto(ProductPriceReadBase):
    """Controller DTO for create product price read operations"""
    pass


class CreateProductPriceServiceReadDto(ProductPriceReadBase):
    """Service DTO for create product price read operations"""
    pass


class UpdateProductPriceControllerReadDto(ProductPriceReadBase):
    """Controller DTO for update product price read operations"""
    pass


class UpdateProductPriceServiceReadDto(ProductPriceReadBase):
    """Service DTO for update product price read operations"""
    pass


class GetProductPriceControllerReadDto(ProductPriceReadBase):
    """Controller DTO for get product price read operations"""
    currency_id: Optional[str] = Field(None, description="Currency ID")
    product_name: Optional[str] = Field(None, description="Product name")


class GetProductPriceServiceReadDto(ProductPriceReadBase):
    """Service DTO for get product price read operations"""
    currency_id: Optional[str] = Field(None, description="Currency ID")
    product_name: Optional[str] = Field(None, description="Product name")


class GetProductPricesControllerReadDto(ProductPriceReadBase):
    """Controller DTO for get product prices list read operations"""
    currency_id: Optional[str] = Field(None, description="Currency ID")
    product_name: Optional[str] = Field(None, description="Product name")


class GetProductPricesServiceReadDto(ProductPriceReadBase):
    """Service DTO for get product prices list read operations"""
    currency_id: Optional[str] = Field(None, description="Currency ID")
    product_name: Optional[str] = Field(None, description="Product name")


class DeleteProductPriceReadBase(BaseModel):
    """Base read DTO for delete product price result"""
    price_id: str
    message: str


class DeleteProductPriceControllerReadDto(DeleteProductPriceReadBase):
    """Controller DTO for delete product price read operations"""
    pass


class DeleteProductPriceServiceReadDto(DeleteProductPriceReadBase):
    """Service DTO for delete product price read operations"""
    pass


# =====================================================
# PRODUCT PRICE STATISTICS READ DTOs
# =====================================================

class ProductPriceStatisticsReadBase(BaseModel):
    """Base read DTO for product price statistics"""
    total_prices: int = Field(default=0, description="Total number of product prices")
    
    # By type
    total_sku: int = Field(default=0, description="Total prices with type SKU")
    total_global: int = Field(default=0, description="Total prices with type GLOBAL")
    total_location: int = Field(default=0, description="Total prices with type LOCATION")
    total_tag: int = Field(default=0, description="Total prices with type TAG")
    total_category: int = Field(default=0, description="Total prices with type CATEGORY")
    total_brand: int = Field(default=0, description="Total prices with type BRAND")
    total_label: int = Field(default=0, description="Total prices with type LABEL")
    
    # Additional statistics
    total_stops_other_prices: int = Field(default=0, description="Total prices that stop other prices")
    average_priority: Optional[Decimal] = Field(default=None, description="Average priority of all prices")


class GetProductPriceStatisticsControllerReadDto(ProductPriceStatisticsReadBase):
    """Controller DTO for product price statistics"""
    pass


class GetProductPriceStatisticsServiceReadDto(ProductPriceStatisticsReadBase):
    """Service DTO for product price statistics"""
    pass

