from typing import Optional
from typing_extensions import Literal
from decimal import Decimal
from pydantic import BaseModel, Field


# =====================================================
# ENUMS AND LITERALS
# =====================================================

ProductPriceType = Literal['SKU', 'GLOBAL', 'LOCATION', 'TAG', 'CATEGORY', 'BRAND', 'LABEL']


# =====================================================
# PRODUCT PRICE BASE DTOs
# =====================================================

class ProductPriceBase(BaseModel):
    """Base DTO for product price information"""
    product_id: str = Field(..., description="ID of the product")
    of_type: ProductPriceType = Field(..., description="Type of price: SKU, GLOBAL, LOCATION, TAG, CATEGORY, BRAND, or LABEL")
    target_id: Optional[str] = Field(None, description="ID of the target. For SKU: the SKU value. For LOCATION: location.id. For TAG/CATEGORY/BRAND/LABEL: product_metadata.id. Not used for GLOBAL")
    price: Decimal = Field(..., decimal_places=2, ge=0, description="Price value (must be >= 0)")
    currency: str = Field(..., min_length=1, description="Currency ID")
    priority: int = Field(default=0, ge=0, description="Priority for price matching (higher priority takes precedence)")
    stops_other_prices: bool = Field(default=False, description="If true, this price stops/overrides other prices and becomes the fixed price")

