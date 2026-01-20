from typing import Optional, List
from typing_extensions import Literal
from pydantic import BaseModel, Field
from decimal import Decimal


# =====================================================
# ENUMS AND LITERALS
# =====================================================

TaxRuleType = Literal['PRODUCT', 'ALL_PRODUCTS', 'CATEGORY', 'TAG', 'BRAND', 'LABEL', 'LOCATION', 'SKU']
ConditionType = Literal['TAX_EXEMPTION', 'TAX_REDUCTION']
Condition = Literal['IF_ITEM_PRICE', 'IF_TOTAL_PRICE', 'IF_ITEM_QTY']
ComparisonOperator = Literal['EQUALS', 'NOT_EQUALS', 'GREATER_THAN', 'LESS_THAN', 'GREATER_THAN_OR_EQUALS', 'LESS_THAN_OR_EQUALS']
LogicalOperator = Literal['AND', 'OR']


# =====================================================
# TAX RULE CONDITION DTOs
# =====================================================

class TaxRuleConditionBase(BaseModel):
    """Base DTO for tax rule condition"""
    description: Optional[str] = Field(None, max_length=1000, description="Description of the condition")
    priority: int = Field(..., ge=0, description="Priority for condition evaluation order (higher priority evaluated first)")
    condition_type: ConditionType = Field(..., description="Type of condition: TAX_EXEMPTION or TAX_REDUCTION")
    condition: Condition = Field(..., description="Condition to check: IF_ITEM_PRICE, IF_TOTAL_PRICE, or IF_ITEM_QTY")
    comparison_operator: ComparisonOperator = Field(..., description="Comparison operator: EQUALS, NOT_EQUALS, GREATER_THAN, LESS_THAN, GREATER_THAN_OR_EQUALS, LESS_THAN_OR_EQUALS")
    comparison_value: Decimal = Field(..., ge=0, description="Value to compare against (must be >= 0)")
    adjustment_value: Optional[Decimal] = Field(None, ge=0, description="Adjustment value for TAX_REDUCTION (must be >= 0 if provided)")
    adjustment_percentage: Optional[Decimal] = Field(None, ge=0, description="Adjustment percentage for TAX_REDUCTION (must be >= 0 if provided)")
    logical_operator: LogicalOperator = Field(..., description="Logical operator: AND or OR")


# =====================================================
# TAX RULE BASE DTOs
# =====================================================

class TaxRuleBase(BaseModel):
    """Base DTO for tax rule information"""
    name: str = Field(..., min_length=1, max_length=255, description="Name of the tax rule")
    description: Optional[str] = Field(None, max_length=1000, description="Description of the tax rule")
    tax_id: str = Field(..., description="ID of the tax to apply")
    rule_type: TaxRuleType = Field(..., description="Type of the rule: PRODUCT, ALL_PRODUCTS, CATEGORY, TAG, BRAND, LABEL, LOCATION, or SKU")
    rule_target_id: Optional[str] = Field(None, description="ID of the target. Required for PRODUCT, SKU, LOCATION, TAG, CATEGORY, BRAND, LABEL. Not used for ALL_PRODUCTS")
    priority: int = Field(default=0, ge=0, description="Priority for rule matching (higher priority takes precedence)")
    is_active: bool = Field(default=True, description="Whether the tax rule is active")
    conditions: Optional[List[TaxRuleConditionBase]] = Field(default=None, description="List of conditions for the tax rule (optional)")

