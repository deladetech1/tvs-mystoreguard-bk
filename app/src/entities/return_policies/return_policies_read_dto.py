from typing import Optional
from datetime import datetime
from decimal import Decimal
from pydantic import BaseModel, Field
from src.entities.return_policies.return_policies_base import ReturnPolicyBase


# =====================================================
# RETURN POLICY READ DTOs
# =====================================================

class ReturnPolicyReadBase(ReturnPolicyBase):
    """Base read DTO for return policy"""
    id: str
    tenant_id: str
    org_id: str
    bus_id: str
    policy_target_name: Optional[str] = Field(None, description="Name of the policy target (e.g., product name, category name)")
    cdate: Optional[str] = None
    ctime: Optional[str] = None
    cdatetime: Optional[datetime] = None
    created_by: Optional[str] = None
    updated_by: Optional[str] = None
    deleted_by: Optional[str] = None


class CreateReturnPolicyControllerReadDto(ReturnPolicyReadBase):
    """Controller DTO for create return policy read operations"""
    pass


class CreateReturnPolicyServiceReadDto(ReturnPolicyReadBase):
    """Service DTO for create return policy read operations"""
    pass


class UpdateReturnPolicyControllerReadDto(ReturnPolicyReadBase):
    """Controller DTO for update return policy read operations"""
    pass


class UpdateReturnPolicyServiceReadDto(ReturnPolicyReadBase):
    """Service DTO for update return policy read operations"""
    pass


class GetReturnPolicyControllerReadDto(ReturnPolicyReadBase):
    """Controller DTO for get return policy read operations"""
    pass


class GetReturnPolicyServiceReadDto(ReturnPolicyReadBase):
    """Service DTO for get return policy read operations"""
    pass


class GetReturnPoliciesControllerReadDto(ReturnPolicyReadBase):
    """Controller DTO for get return policies list read operations"""
    pass


class GetReturnPoliciesServiceReadDto(ReturnPolicyReadBase):
    """Service DTO for get return policies list read operations"""
    pass


class DeleteReturnPolicyReadBase(BaseModel):
    """Base read DTO for delete return policy result"""
    policy_id: str
    message: str


class DeleteReturnPolicyControllerReadDto(DeleteReturnPolicyReadBase):
    """Controller DTO for delete return policy read operations"""
    pass


class DeleteReturnPolicyServiceReadDto(DeleteReturnPolicyReadBase):
    """Service DTO for delete return policy read operations"""
    pass


# =====================================================
# RETURN POLICY STATISTICS READ DTOs
# =====================================================

class ReturnPolicyStatisticsReadBase(BaseModel):
    """Base read DTO for return policy statistics"""
    total_policies: int = Field(default=0, description="Total number of return policies")
    total_active: int = Field(default=0, description="Total number of active return policies")
    total_inactive: int = Field(default=0, description="Total number of inactive return policies")

    # By target type (most common/important)
    total_target_all_products: int = Field(default=0, description="Total policies targeting ALL_PRODUCTS")
    total_target_category: int = Field(default=0, description="Total policies targeting CATEGORY")
    total_target_product: int = Field(default=0, description="Total policies targeting PRODUCT")
    total_target_location: int = Field(default=0, description="Total policies targeting LOCATION")

    # By return window
    total_non_returnable: int = Field(default=0, description="Total policies with return_window_days = 0 (non-returnable)")
    total_with_restocking_fee: int = Field(default=0, description="Total policies with restocking_fee_percent > 0")
    total_approval_required: int = Field(default=0, description="Total policies requiring approval")

    # Additional statistics
    total_stops_other_policies: int = Field(default=0, description="Total policies that stop other policies")
    average_priority: Optional[Decimal] = Field(default=None, description="Average priority of all policies")
    average_return_window_days: Optional[Decimal] = Field(default=None, description="Average return window in days")


class GetReturnPolicyStatisticsControllerReadDto(ReturnPolicyStatisticsReadBase):
    """Controller DTO for return policy statistics"""
    pass


class GetReturnPolicyStatisticsServiceReadDto(ReturnPolicyStatisticsReadBase):
    """Service DTO for return policy statistics"""
    pass
