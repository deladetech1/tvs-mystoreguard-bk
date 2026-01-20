from typing import Optional
from typing_extensions import Literal
from decimal import Decimal
from datetime import datetime
from pydantic import BaseModel, Field


# =====================================================
# ENUMS AND LITERALS
# =====================================================

PricingRuleCategory = Literal['PRICE_ADJUSTMENT', 'QUANTITY_BASED']
PricingRuleType = Literal[
    'FIXED_PRICE',
    'FIXED_AMOUNT',
    'PRICE_DISCOUNT',
    'PERCENTAGE_DISCOUNT',
    'PRICE_MARKUP',
    'PERCENTAGE_MARKUP',
    'BUNDLE',
    'BOGO',
    'QUANTITY_BREAK'
]
PricingRuleTargetType = Literal['PRODUCT', 'ALL_PRODUCTS', 'SKU', 'LOCATION', 'TAG', 'CATEGORY', 'BRAND', 'LABEL']


# =====================================================
# PRICING RULE BASE DTOs
# =====================================================

class PricingRuleBase(BaseModel):
    """Base DTO for pricing rule information"""
    name: str = Field(..., min_length=1, max_length=255, description="Name of the pricing rule")
    rule_category: PricingRuleCategory = Field(..., description="Category of the rule: PRICE_ADJUSTMENT or QUANTITY_BASED")
    rule_type: PricingRuleType = Field(..., description="Type of the rule")
    rule_target_type: PricingRuleTargetType = Field(..., description="Target type for the rule")
    rule_target_id: Optional[str] = Field(None, description="ID of the target. Required for PRODUCT, SKU, LOCATION, TAG, CATEGORY, BRAND, LABEL. Not used for ALL_PRODUCTS")
    
    # Quantity based rules
    quantity_min: Optional[int] = Field(None, ge=0, description="Minimum quantity for quantity-based rules")
    quantity_max: Optional[int] = Field(None, ge=0, description="Maximum quantity for quantity-based rules")
    
    # Price adjustments
    discount_value: Optional[Decimal] = Field(None, decimal_places=2, description="Fixed discount/markup value (e.g., -5.00 or +5.00)")
    discount_percent: Optional[Decimal] = Field(None, decimal_places=2, ge=-100, le=100, description="Percentage discount/markup (e.g., -10.00 or +10.00)")
    
    # BOGO / BUNDLE / QUANTITY_BREAK
    free_qty: int = Field(default=0, ge=0, description="Free quantity (e.g., Buy 2 get 1 free)")
    
    # Rule behavior
    stops_other_rules: bool = Field(default=False, description="If true, this rule stops/overrides other rules")
    priority: int = Field(default=0, ge=0, description="Priority for rule matching (higher priority takes precedence)")
    
    # Time-based filters
    start_datetime: Optional[datetime] = Field(None, description="Start date and time for the rule")
    end_datetime: Optional[datetime] = Field(None, description="End date and time for the rule")
    
    # Active status
    is_active: bool = Field(default=True, description="Whether the pricing rule is active")

