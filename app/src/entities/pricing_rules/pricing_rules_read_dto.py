from typing import Optional
from datetime import datetime
from decimal import Decimal
from pydantic import BaseModel, Field
from src.entities.pricing_rules.pricing_rules_base import PricingRuleBase


# =====================================================
# PRICING RULE READ DTOs
# =====================================================

class PricingRuleReadBase(PricingRuleBase):
    """Base read DTO for pricing rule"""
    id: str
    tenant_id: str
    org_id: str
    bus_id: str
    rule_target_name: Optional[str] = Field(None, description="Name of the rule target (e.g., product name, category name)")
    cdate: Optional[str] = None
    ctime: Optional[str] = None
    cdatetime: Optional[datetime] = None
    created_by: Optional[str] = None
    updated_by: Optional[str] = None
    deleted_by: Optional[str] = None


class CreatePricingRuleControllerReadDto(PricingRuleReadBase):
    """Controller DTO for create pricing rule read operations"""
    pass


class CreatePricingRuleServiceReadDto(PricingRuleReadBase):
    """Service DTO for create pricing rule read operations"""
    pass


class UpdatePricingRuleControllerReadDto(PricingRuleReadBase):
    """Controller DTO for update pricing rule read operations"""
    pass


class UpdatePricingRuleServiceReadDto(PricingRuleReadBase):
    """Service DTO for update pricing rule read operations"""
    pass


class GetPricingRuleControllerReadDto(PricingRuleReadBase):
    """Controller DTO for get pricing rule read operations"""
    pass


class GetPricingRuleServiceReadDto(PricingRuleReadBase):
    """Service DTO for get pricing rule read operations"""
    pass


class GetPricingRulesControllerReadDto(PricingRuleReadBase):
    """Controller DTO for get pricing rules list read operations"""
    pass


class GetPricingRulesServiceReadDto(PricingRuleReadBase):
    """Service DTO for get pricing rules list read operations"""
    pass


class DeletePricingRuleReadBase(BaseModel):
    """Base read DTO for delete pricing rule result"""
    rule_id: str
    message: str


class DeletePricingRuleControllerReadDto(DeletePricingRuleReadBase):
    """Controller DTO for delete pricing rule read operations"""
    pass


class DeletePricingRuleServiceReadDto(DeletePricingRuleReadBase):
    """Service DTO for delete pricing rule read operations"""
    pass


# =====================================================
# PRICING RULE STATISTICS READ DTOs
# =====================================================

class PricingRuleStatisticsReadBase(BaseModel):
    """Base read DTO for pricing rule statistics"""
    total_rules: int = Field(default=0, description="Total number of pricing rules")
    total_active: int = Field(default=0, description="Total number of active pricing rules")
    total_inactive: int = Field(default=0, description="Total number of inactive pricing rules")
    
    # By category
    total_price_adjustment: int = Field(default=0, description="Total rules with category PRICE_ADJUSTMENT")
    total_quantity_based: int = Field(default=0, description="Total rules with category QUANTITY_BASED")
    
    # By target type (most common/important)
    total_target_all_products: int = Field(default=0, description="Total rules targeting ALL_PRODUCTS")
    total_target_category: int = Field(default=0, description="Total rules targeting CATEGORY")
    total_target_location: int = Field(default=0, description="Total rules targeting LOCATION")
    
    # Additional statistics
    total_stops_other_rules: int = Field(default=0, description="Total rules that stop other rules")
    average_priority: Optional[Decimal] = Field(default=None, description="Average priority of all rules")


class GetPricingRuleStatisticsControllerReadDto(PricingRuleStatisticsReadBase):
    """Controller DTO for pricing rule statistics"""
    pass


class GetPricingRuleStatisticsServiceReadDto(PricingRuleStatisticsReadBase):
    """Service DTO for pricing rule statistics"""
    pass

