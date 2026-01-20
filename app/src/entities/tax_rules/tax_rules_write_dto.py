from typing import Optional, List
from pydantic import BaseModel, Field
from src.entities.tax_rules.tax_rules_base import TaxRuleBase, TaxRuleConditionBase


# =====================================================
# CREATE TAX RULE WRITE DTOs
# =====================================================

class CreateTaxRuleWriteBase(TaxRuleBase):
    """Base write DTO for creating a tax rule"""
    pass


class CreateTaxRuleControllerWriteDto(CreateTaxRuleWriteBase):
    """Controller DTO for creating a tax rule"""
    pass


class CreateTaxRuleServiceWriteDto(CreateTaxRuleWriteBase):
    """Service DTO for creating a tax rule"""
    pass


# =====================================================
# UPDATE TAX RULE WRITE DTOs
# =====================================================

class UpdateTaxRuleWriteBase(BaseModel):
    """Base write DTO for updating a tax rule"""
    name: Optional[str] = Field(None, min_length=1, max_length=255, description="Name of the tax rule")
    description: Optional[str] = Field(None, max_length=1000, description="Description of the tax rule")
    tax_id: Optional[str] = Field(None, description="ID of the tax to apply")
    rule_type: Optional[str] = Field(None, description="Type of the rule")
    rule_target_id: Optional[str] = Field(None, description="ID of the target")
    priority: Optional[int] = Field(None, ge=0, description="Priority for rule matching")
    is_active: Optional[bool] = Field(None, description="Whether the tax rule is active")
    conditions: Optional[List[TaxRuleConditionBase]] = Field(default=None, description="List of conditions for the tax rule. If provided, replaces all existing conditions. If empty list [], removes all conditions.")


class UpdateTaxRuleControllerWriteDto(UpdateTaxRuleWriteBase):
    """Controller DTO for updating a tax rule"""
    pass


class UpdateTaxRuleServiceWriteDto(UpdateTaxRuleWriteBase):
    """Service DTO for updating a tax rule"""
    pass


# =====================================================
# DELETE TAX RULE WRITE DTOs
# =====================================================

class DeleteTaxRuleWriteBase(BaseModel):
    """Base write DTO for deleting a tax rule"""
    rule_id: str = Field(..., description="ID of the rule to delete")


class DeleteTaxRuleControllerWriteDto(DeleteTaxRuleWriteBase):
    """Controller DTO for deleting a tax rule"""
    pass


class DeleteTaxRuleServiceWriteDto(DeleteTaxRuleWriteBase):
    """Service DTO for deleting a tax rule"""
    pass

