from typing import Optional, List
from typing_extensions import Literal
from pydantic import BaseModel, Field
from datetime import date
from decimal import Decimal


# =====================================================
# ENUMS AND LITERALS
# =====================================================

PromoCodeDiscountType = Literal['PERCENTAGE', 'FIXED_AMOUNT', 'FREE_SHIPPING']
PromoCodeStatusType = Literal['ACTIVE', 'INACTIVE', 'EXPIRED']
DeleteStatusType = Literal['PENDING', 'DELETED', 'NOT_DELETED']


# =====================================================
# PROMO CODE BASE DTOs
# =====================================================

class PromoCodeBase(BaseModel):
    """Base DTO for promo code information"""
    promo_code: str = Field(..., min_length=1, description="Unique promo code")
    currency_id: str = Field(..., description="Currency ID for the promo code")
    discount_type: PromoCodeDiscountType = Field(..., description="Discount type: PERCENTAGE, FIXED_AMOUNT, or FREE_SHIPPING")
    discount_value: Decimal = Field(..., ge=0, decimal_places=2, description="Discount value: For PERCENTAGE, this is the percentage (e.g., 10 for 10%). For FIXED_AMOUNT, this is the fixed discount amount (e.g., 50 for $50 off). For FREE_SHIPPING, this can be 0.")
    min_purchase_amount: Optional[Decimal] = Field(default=0, ge=0, decimal_places=2, description="Minimum purchase amount to apply discount")
    max_discount_amount: Optional[Decimal] = Field(None, ge=0, decimal_places=2, description="Maximum discount amount (for percentage discounts)")
    usage_limit_per_customer: Optional[int] = Field(None, ge=1, description="Usage limit per customer (null = unlimited)")
    total_usage_limit: Optional[int] = Field(None, ge=1, description="Total usage limit (null = unlimited)")
    start_date: Optional[date] = Field(None, description="Start date (defaults to current date)")
    end_date: Optional[date] = Field(None, description="End date (optional)")
    status: PromoCodeStatusType = Field(default='ACTIVE', description="Promo code status")
    applicable_to_customers_only: bool = Field(default=False, description="Whether promo code is only applicable to registered customers")
    applicable_to_locations: List[str] = Field(..., min_items=1, description="List of location IDs where this promo code can be used (at least one location required)")
    applicable_to_products: Optional[List[str]] = Field(None, description="List of product IDs this promo applies to (for product-specific discounts). If set, applicable_to_product_metadata should be null.")
    applicable_to_product_metadata: Optional[List[str]] = Field(None, description="List of product metadata IDs (categories, brands, tags, labels) this promo applies to. If set, applicable_to_products should be null.")
    description: Optional[str] = Field(None, description="Description")
    notes: Optional[str] = Field(None, description="Additional notes")
    is_active: bool = Field(default=True, description="Whether the promo code is active")

