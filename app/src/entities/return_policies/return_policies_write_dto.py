from typing import Optional
from decimal import Decimal
from datetime import datetime
from pydantic import BaseModel, Field
from src.entities.return_policies.return_policies_base import ReturnPolicyBase


# =====================================================
# CREATE RETURN POLICY WRITE DTOs
# =====================================================

class CreateReturnPolicyWriteBase(ReturnPolicyBase):
    """Base write DTO for creating a return policy"""
    pass


class CreateReturnPolicyControllerWriteDto(CreateReturnPolicyWriteBase):
    """Controller DTO for creating a return policy"""
    pass


class CreateReturnPolicyServiceWriteDto(CreateReturnPolicyWriteBase):
    """Service DTO for creating a return policy"""
    pass


# =====================================================
# UPDATE RETURN POLICY WRITE DTOs
# =====================================================

class UpdateReturnPolicyWriteBase(BaseModel):
    """Base write DTO for updating a return policy"""
    name: Optional[str] = Field(None, min_length=1, max_length=255, description="Name of the return policy")
    description: Optional[str] = Field(None, max_length=1000, description="Description of the return policy")

    # Target
    policy_target_type: Optional[str] = Field(None, description="Target type for the policy")
    policy_target_id: Optional[str] = Field(None, description="ID of the target")

    # Return rules
    return_window_days: Optional[int] = Field(None, ge=0, description="Number of days after purchase within which a return is accepted")
    condition_required: Optional[str] = Field(None, description="Condition required for the item to be returnable")
    receipt_required: Optional[bool] = Field(None, description="Whether a receipt is required")
    allow_expired_returns: Optional[bool] = Field(None, description="Whether to accept returns of expired items")

    # Refund rules
    restocking_fee_percent: Optional[Decimal] = Field(None, ge=0, le=100, decimal_places=2, description="Restocking fee percentage")
    refund_method: Optional[str] = Field(None, description="Allowed refund method")

    # Approval
    approval_required: Optional[bool] = Field(None, description="Whether manager approval is required")
    approval_threshold_amount: Optional[Decimal] = Field(None, ge=0, decimal_places=2, description="Approval threshold amount")

    # Policy behavior
    stops_other_policies: Optional[bool] = Field(None, description="If true, this policy stops other policies")
    priority: Optional[int] = Field(None, ge=0, description="Priority for policy matching")

    # Time-based activation
    start_datetime: Optional[datetime] = Field(None, description="Start date and time for the policy")
    end_datetime: Optional[datetime] = Field(None, description="End date and time for the policy")

    # Active status
    is_active: Optional[bool] = Field(None, description="Whether the return policy is active")


class UpdateReturnPolicyControllerWriteDto(UpdateReturnPolicyWriteBase):
    """Controller DTO for updating a return policy"""
    pass


class UpdateReturnPolicyServiceWriteDto(UpdateReturnPolicyWriteBase):
    """Service DTO for updating a return policy"""
    pass


# =====================================================
# DELETE RETURN POLICY WRITE DTOs
# =====================================================

class DeleteReturnPolicyWriteBase(BaseModel):
    """Base write DTO for deleting a return policy"""
    policy_id: str = Field(..., description="ID of the policy to delete")


class DeleteReturnPolicyControllerWriteDto(DeleteReturnPolicyWriteBase):
    """Controller DTO for deleting a return policy"""
    pass


class DeleteReturnPolicyServiceWriteDto(DeleteReturnPolicyWriteBase):
    """Service DTO for deleting a return policy"""
    pass
