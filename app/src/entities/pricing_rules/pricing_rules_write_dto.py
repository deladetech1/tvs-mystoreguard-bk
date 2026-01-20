from typing import Optional
from decimal import Decimal
from datetime import datetime
from pydantic import BaseModel, Field
from src.entities.pricing_rules.pricing_rules_base import PricingRuleBase


# =====================================================
# CREATE PRICING RULE WRITE DTOs
# =====================================================

class CreatePricingRuleWriteBase(PricingRuleBase):
    """Base write DTO for creating a pricing rule"""
    pass


class CreatePricingRuleControllerWriteDto(CreatePricingRuleWriteBase):
    """Controller DTO for creating a pricing rule"""
    pass


class CreatePricingRuleServiceWriteDto(CreatePricingRuleWriteBase):
    """Service DTO for creating a pricing rule"""
    pass


# =====================================================
# UPDATE PRICING RULE WRITE DTOs
# =====================================================

class UpdatePricingRuleWriteBase(BaseModel):
    """Base write DTO for updating a pricing rule"""
    name: Optional[str] = Field(None, min_length=1, max_length=255, description="Name of the pricing rule")
    rule_category: Optional[str] = Field(None, description="Category of the rule: PRICE_ADJUSTMENT or QUANTITY_BASED")
    rule_type: Optional[str] = Field(None, description="Type of the rule")
    rule_target_type: Optional[str] = Field(None, description="Target type for the rule")
    rule_target_id: Optional[str] = Field(None, description="ID of the target")
    
    # Quantity based rules
    quantity_min: Optional[int] = Field(None, ge=0, description="Minimum quantity for quantity-based rules")
    quantity_max: Optional[int] = Field(None, ge=0, description="Maximum quantity for quantity-based rules")
    
    # Price adjustments
    discount_value: Optional[Decimal] = Field(None, decimal_places=2, description="Fixed discount/markup value")
    discount_percent: Optional[Decimal] = Field(None, decimal_places=2, ge=-100, le=100, description="Percentage discount/markup")
    
    # BOGO / BUNDLE / QUANTITY_BREAK
    free_qty: Optional[int] = Field(None, ge=0, description="Free quantity")
    
    # Rule behavior
    stops_other_rules: Optional[bool] = Field(None, description="If true, this rule stops/overrides other rules")
    priority: Optional[int] = Field(None, ge=0, description="Priority for rule matching")
    
    # Time-based filters
    start_datetime: Optional[datetime] = Field(None, description="Start date and time for the rule")
    end_datetime: Optional[datetime] = Field(None, description="End date and time for the rule")
    
    # Active status
    is_active: Optional[bool] = Field(None, description="Whether the pricing rule is active")


class UpdatePricingRuleControllerWriteDto(UpdatePricingRuleWriteBase):
    """Controller DTO for updating a pricing rule"""
    pass


class UpdatePricingRuleServiceWriteDto(UpdatePricingRuleWriteBase):
    """Service DTO for updating a pricing rule"""
    pass


# =====================================================
# DELETE PRICING RULE WRITE DTOs
# =====================================================

class DeletePricingRuleWriteBase(BaseModel):
    """Base write DTO for deleting a pricing rule"""
    rule_id: str = Field(..., description="ID of the rule to delete")


class DeletePricingRuleControllerWriteDto(DeletePricingRuleWriteBase):
    """Controller DTO for deleting a pricing rule"""
    pass


class DeletePricingRuleServiceWriteDto(DeletePricingRuleWriteBase):
    """Service DTO for deleting a pricing rule"""
    pass

