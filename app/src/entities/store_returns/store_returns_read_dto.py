from typing import Optional, List
from datetime import datetime
from decimal import Decimal
from pydantic import BaseModel, Field
from src.entities.store_returns.store_returns_base import (
    ReturnStatusType,
    ReturnType,
    ReturnReasonType,
    ReturnItemConditionType,
    RefundMethodType,
)


# =====================================================
# RETURN ITEM READ DTOs
# =====================================================

class ReturnItemReadBase(BaseModel):
    """Base read DTO for return item"""
    id: str
    tenant_id: str
    org_id: str
    bus_id: str
    loc_id: str
    return_id: str
    sale_item_id: str
    product_id: str
    product_name: str
    batch_id: Optional[str] = None
    quantity_returned: float
    condition: ReturnItemConditionType
    restock: bool = Field(default=True, description="Whether this item was restocked")
    unit_refund_amount: float = Field(default=0, description="Refund amount per unit")
    line_refund_amount: float = Field(default=0, description="Total refund for this line (unit_refund_amount * quantity_returned)")
    reason: Optional[str] = None
    cdate: Optional[str] = None
    ctime: Optional[str] = None
    cdatetime: Optional[datetime] = None
    created_by: Optional[str] = None


# =====================================================
# RETURN READ DTOs
# =====================================================

class ReturnReadBase(BaseModel):
    """Base read DTO for return"""
    id: str
    tenant_id: str
    org_id: str
    bus_id: str
    loc_id: str
    sale_id: str
    sale_number: Optional[str] = None
    return_number: str
    return_date: Optional[str] = None
    return_type: ReturnType
    status: ReturnStatusType
    reason: ReturnReasonType
    reason_notes: Optional[str] = None
    refund_method: RefundMethodType
    # Calculated amounts
    subtotal_refund_amount: float = Field(default=0, description="Sum of all item refunds before restocking fee")
    restocking_fee_percent: float = Field(default=0, description="Restocking fee percentage applied")
    restocking_fee_amount: float = Field(default=0, description="Restocking fee deducted")
    total_refund_amount: float = Field(default=0, description="Final refund amount after restocking fee")
    # Policy reference
    return_policy_id: Optional[str] = None
    return_policy_name: Optional[str] = None
    # Approval
    approval_required: bool = Field(default=False)
    approved_by: Optional[str] = None
    approved_at: Optional[datetime] = None
    rejected_by: Optional[str] = None
    rejected_at: Optional[datetime] = None
    rejection_reason: Optional[str] = None
    # Processing
    processed_by: Optional[str] = None
    processed_at: Optional[datetime] = None
    processing_notes: Optional[str] = None
    # Customer
    customer_id: Optional[str] = None
    customer_name: Optional[str] = None
    # Audit
    cdate: Optional[str] = None
    ctime: Optional[str] = None
    cdatetime: Optional[datetime] = None
    created_by: Optional[str] = None
    updated_by: Optional[str] = None
    # Items
    items: List[ReturnItemReadBase] = Field(default_factory=list, description="List of return items")


class CreateReturnControllerReadDto(ReturnReadBase):
    """Controller DTO for create return read operations"""
    pass


class CreateReturnServiceReadDto(ReturnReadBase):
    """Service DTO for create return read operations"""
    pass


class ApproveReturnControllerReadDto(ReturnReadBase):
    """Controller DTO for approve return read operations"""
    pass


class ApproveReturnServiceReadDto(ReturnReadBase):
    """Service DTO for approve return read operations"""
    pass


class RejectReturnControllerReadDto(ReturnReadBase):
    """Controller DTO for reject return read operations"""
    pass


class RejectReturnServiceReadDto(ReturnReadBase):
    """Service DTO for reject return read operations"""
    pass


class ProcessReturnControllerReadDto(ReturnReadBase):
    """Controller DTO for process return read operations"""
    pass


class ProcessReturnServiceReadDto(ReturnReadBase):
    """Service DTO for process return read operations"""
    pass


class GetReturnControllerReadDto(ReturnReadBase):
    """Controller DTO for get return read operations"""
    pass


class GetReturnServiceReadDto(ReturnReadBase):
    """Service DTO for get return read operations"""
    pass


class GetReturnsControllerReadDto(ReturnReadBase):
    """Controller DTO for get returns list read operations"""
    pass


class GetReturnsServiceReadDto(ReturnReadBase):
    """Service DTO for get returns list read operations"""
    pass


# =====================================================
# RETURN STATISTICS READ DTOs
# =====================================================

class ReturnStatisticsReadBase(BaseModel):
    """Base read DTO for return statistics"""
    total_returns: int = Field(default=0)
    total_pending: int = Field(default=0)
    total_approved: int = Field(default=0)
    total_rejected: int = Field(default=0)
    total_completed: int = Field(default=0)
    total_refund_amount: float = Field(default=0, description="Total refunded amount across all completed returns")
    total_restocking_fees: float = Field(default=0, description="Total restocking fees collected")
    total_items_returned: float = Field(default=0, description="Total quantity of items returned")
    total_items_restocked: float = Field(default=0, description="Total quantity of items restocked to inventory")
    total_items_written_off: float = Field(default=0, description="Total quantity of items written off")


class GetReturnStatisticsControllerReadDto(ReturnStatisticsReadBase):
    """Controller DTO for return statistics"""
    pass


class GetReturnStatisticsServiceReadDto(ReturnStatisticsReadBase):
    """Service DTO for return statistics"""
    pass
