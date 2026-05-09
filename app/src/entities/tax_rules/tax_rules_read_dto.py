from typing import Optional, List
from datetime import datetime
from decimal import Decimal
from pydantic import BaseModel, Field
from src.entities.tax_rules.tax_rules_base import TaxRuleBase, TaxRuleConditionBase


# =====================================================
# TAX RULE CONDITION READ DTO
# =====================================================

class TaxRuleConditionReadDto(TaxRuleConditionBase):
    """Read DTO for a tax rule condition (includes persisted identifiers)"""
    id: str
    tax_rule_id: Optional[str] = None


# =====================================================
# TAX RULE READ DTOs
# =====================================================

class TaxRuleReadBase(TaxRuleBase):
    """Base read DTO for tax rule"""
    id: str
    tenant_id: str
    org_id: str
    bus_id: str
    tax_name: Optional[str] = Field(None, description="Name of the tax associated with this rule")
    rule_target_name: Optional[str] = Field(None, description="Name/value of the rule target (product name, location name, metadata name, etc.)")
    conditions: Optional[List[TaxRuleConditionReadDto]] = Field(default=None, description="List of conditions attached to the tax rule")
    cdate: Optional[str] = None
    ctime: Optional[str] = None
    cdatetime: Optional[datetime] = None
    created_by: Optional[str] = None
    updated_by: Optional[str] = None
    deleted_by: Optional[str] = None


class CreateTaxRuleControllerReadDto(TaxRuleReadBase):
    """Controller DTO for create tax rule read operations"""
    pass


class CreateTaxRuleServiceReadDto(TaxRuleReadBase):
    """Service DTO for create tax rule read operations"""
    pass


class UpdateTaxRuleControllerReadDto(TaxRuleReadBase):
    """Controller DTO for update tax rule read operations"""
    pass


class UpdateTaxRuleServiceReadDto(TaxRuleReadBase):
    """Service DTO for update tax rule read operations"""
    pass


class GetTaxRuleControllerReadDto(TaxRuleReadBase):
    """Controller DTO for get tax rule read operations"""
    pass


class GetTaxRuleServiceReadDto(TaxRuleReadBase):
    """Service DTO for get tax rule read operations"""
    pass


class GetTaxRulesControllerReadDto(TaxRuleReadBase):
    """Controller DTO for get tax rules list read operations"""
    pass


class GetTaxRulesServiceReadDto(TaxRuleReadBase):
    """Service DTO for get tax rules list read operations"""
    pass


class DeleteTaxRuleReadBase(BaseModel):
    """Base read DTO for delete tax rule result"""
    rule_id: str
    message: str


class DeleteTaxRuleControllerReadDto(DeleteTaxRuleReadBase):
    """Controller DTO for delete tax rule read operations"""
    pass


class DeleteTaxRuleServiceReadDto(DeleteTaxRuleReadBase):
    """Service DTO for delete tax rule read operations"""
    pass


# =====================================================
# TAX RULE STATISTICS READ DTOs
# =====================================================

class TaxRuleStatisticsReadBase(BaseModel):
    """Base read DTO for tax rule statistics"""
    total_rules: int = Field(default=0, description="Total number of tax rules")
    total_active: int = Field(default=0, description="Total number of active tax rules")
    total_inactive: int = Field(default=0, description="Total number of inactive tax rules")
    
    # By rule type
    total_product: int = Field(default=0, description="Total rules with rule_type PRODUCT")
    total_all_products: int = Field(default=0, description="Total rules with rule_type ALL_PRODUCTS")
    total_category: int = Field(default=0, description="Total rules with rule_type CATEGORY")
    total_tag: int = Field(default=0, description="Total rules with rule_type TAG")
    total_brand: int = Field(default=0, description="Total rules with rule_type BRAND")
    total_label: int = Field(default=0, description="Total rules with rule_type LABEL")
    total_location: int = Field(default=0, description="Total rules with rule_type LOCATION")
    total_sku: int = Field(default=0, description="Total rules with rule_type SKU")
    
    # Priority statistics
    average_priority: Optional[Decimal] = Field(default=None, description="Average priority of all rules")
    highest_priority: Optional[int] = Field(default=None, description="Highest priority value")
    lowest_priority: Optional[int] = Field(default=None, description="Lowest priority value")
    
    # Additional statistics
    unique_taxes_count: int = Field(default=0, description="Number of unique taxes with rules")


class GetTaxRuleStatisticsControllerReadDto(TaxRuleStatisticsReadBase):
    """Controller DTO for tax rule statistics"""
    pass


class GetTaxRuleStatisticsServiceReadDto(TaxRuleStatisticsReadBase):
    """Service DTO for tax rule statistics"""
    pass

