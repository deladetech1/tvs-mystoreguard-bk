from typing import Optional, List
from typing_extensions import Literal
from decimal import Decimal
from datetime import datetime
from pydantic import BaseModel, Field


# =====================================================
# ENUMS AND LITERALS
# =====================================================

ReturnPolicyTargetType = Literal['PRODUCT', 'ALL_PRODUCTS', 'SKU', 'LOCATION', 'TAG', 'CATEGORY', 'BRAND', 'LABEL']
ConditionRequiredType = Literal['ANY', 'UNOPENED', 'WITH_TAGS', 'UNDAMAGED']
RefundMethodType = Literal['ORIGINAL_PAYMENT', 'STORE_CREDIT', 'CASH', 'ANY']


# =====================================================
# RETURN POLICY BASE DTOs
# =====================================================

class ReturnPolicyBase(BaseModel):
    """Base DTO for return policy information"""
    name: str = Field(..., min_length=1, max_length=255, description="Name of the return policy")
    description: Optional[str] = Field(None, max_length=1000, description="Description of the return policy")

    # Target (the "applies to" pattern - same as pricing rules)
    policy_target_type: ReturnPolicyTargetType = Field(..., description="Target type for the policy")
    policy_target_id: Optional[str] = Field(None, description="ID of the target. Required for PRODUCT, SKU, LOCATION, TAG, CATEGORY, BRAND, LABEL. Not used for ALL_PRODUCTS")

    # Return rules
    return_window_days: int = Field(..., ge=0, description="Number of days after purchase within which a return is accepted. 0 means non-returnable")
    condition_required: ConditionRequiredType = Field(default='ANY', description="Condition required for the item to be returnable")
    receipt_required: bool = Field(default=True, description="Whether a receipt/proof of purchase is required")
    allow_expired_returns: bool = Field(default=False, description="Whether to accept returns of expired items (refund but write off, not restock)")

    # Refund rules
    restocking_fee_percent: Decimal = Field(default=Decimal('0.00'), ge=0, le=100, decimal_places=2, description="Restocking fee percentage deducted from refund")
    refund_method: RefundMethodType = Field(default='ANY', description="Allowed refund method")

    # Approval
    approval_required: bool = Field(default=False, description="Whether manager approval is required for returns under this policy")
    approvers: Optional[List[str]] = Field(None, description="List of email addresses of users who can approve returns under this policy. If empty and approval_required is true, anyone with the approve permission can approve.")
    approval_threshold_amount: Optional[Decimal] = Field(None, gt=0, decimal_places=2, description="If set, approval is only required when refund amount exceeds this threshold. Must be greater than 0.")

    # Policy behavior
    stops_other_policies: bool = Field(default=False, description="If true, this policy stops/overrides other policies from being evaluated")
    priority: int = Field(default=0, ge=0, description="Priority for policy matching (higher priority takes precedence)")

    # Time-based activation
    start_datetime: Optional[datetime] = Field(None, description="Start date and time for the policy")
    end_datetime: Optional[datetime] = Field(None, description="End date and time for the policy")

    # Active status
    is_active: bool = Field(default=True, description="Whether the return policy is active")
