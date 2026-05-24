from typing import Optional, List
from datetime import datetime
from decimal import Decimal
from pydantic import BaseModel, Field


# =====================================================
# STORE TRANSFER READ DTOs
# =====================================================

class StoreTransferItemRead(BaseModel):
    """A single product line within a store transfer"""
    id: str
    product_id: str
    qty: int
    status: str
    product_name: Optional[str] = Field(None, description="Product name")


class StoreTransferApprovalRead(BaseModel):
    """An approve/reject decision recorded against a store transfer"""
    id: str
    action: str = Field(..., description="APPROVED or REJECTED")
    reason: Optional[str] = Field(None, description="Optional reason/message provided by the approver")
    performed_by: str = Field(..., description="User ID of the approver")
    performed_by_name: Optional[str] = Field(None, description="Full name of the approver")
    cdate: Optional[str] = None
    ctime: Optional[str] = None
    cdatetime: Optional[datetime] = None


class StoreTransferReadBase(BaseModel):
    """Base read DTO for store transfer"""
    id: str
    tenant_id: str
    org_id: str
    bus_id: str
    source: str
    source_id: str
    destination: str
    destination_id: str
    status: str
    transfer_number: str
    person_to_approve_id: Optional[str] = None
    description: Optional[str] = None
    cdate: str
    ctime: str
    cdatetime: datetime
    created_by: str
    items: List[StoreTransferItemRead] = Field(default_factory=list, description="Products being transferred")
    total_qty: int = Field(0, description="Sum of quantities across all items")
    approvals: List[StoreTransferApprovalRead] = Field(default_factory=list, description="Approve/reject decision history")
    source_location_name: Optional[str] = Field(None, description="Source location name")
    destination_location_name: Optional[str] = Field(None, description="Destination location name")
    created_by_name: Optional[str] = Field(None, description="Creator full name")
    approver_name: Optional[str] = Field(None, description="Approver full name")
    source_type: Optional[str] = Field(None, description="Source type (STORE or WAREHOUSE)")
    destination_type: Optional[str] = Field(None, description="Destination type (STORE or WAREHOUSE)")


class CreateStoreTransferControllerReadDto(StoreTransferReadBase):
    """Controller read DTO for creating a store transfer"""
    pass


class CreateStoreTransferServiceReadDto(StoreTransferReadBase):
    """Service read DTO for creating a store transfer"""
    pass


class GetStoreTransferControllerReadDto(StoreTransferReadBase):
    """Controller read DTO for getting a store transfer"""
    pass


class GetStoreTransferServiceReadDto(StoreTransferReadBase):
    """Service read DTO for getting a store transfer"""
    pass


class GetStoreTransfersControllerReadDto(StoreTransferReadBase):
    """Controller read DTO for listing store transfers"""
    pass


class GetStoreTransfersServiceReadDto(StoreTransferReadBase):
    """Service read DTO for listing store transfers"""
    pass


class ApproveStoreTransferControllerReadDto(StoreTransferReadBase):
    """Controller read DTO for approving/rejecting a store transfer"""
    pass


class ApproveStoreTransferServiceReadDto(StoreTransferReadBase):
    """Service read DTO for approving/rejecting a store transfer"""
    pass


class UpdateStoreTransferControllerReadDto(StoreTransferReadBase):
    """Controller read DTO for updating a store transfer"""
    pass


class UpdateStoreTransferServiceReadDto(StoreTransferReadBase):
    """Service read DTO for updating a store transfer"""
    pass


# =====================================================
# DELETE STORE TRANSFER READ DTOs
# =====================================================

class DeleteStoreTransferReadBase(BaseModel):
    """Base read DTO for deleting a store transfer"""
    success: bool = True
    message: str = "Store transfer deleted successfully"


class DeleteStoreTransferControllerReadDto(DeleteStoreTransferReadBase):
    """Controller read DTO for deleting a store transfer"""
    pass


class DeleteStoreTransferServiceReadDto(DeleteStoreTransferReadBase):
    """Service read DTO for deleting a store transfer"""
    pass


# =====================================================
# STORE TRANSFER STATISTICS READ DTOs
# =====================================================

class StoreTransferStatisticsReadBase(BaseModel):
    """Base read DTO for store transfer statistics"""
    total_transfers: int = 0
    total_pending_approval: int = 0
    total_approved: int = 0
    total_rejected: int = 0
    total_completed: int = 0
    total_quantity: Decimal = Field(default=Decimal('0'), decimal_places=2)
    total_quantity_pending: Decimal = Field(default=Decimal('0'), decimal_places=2)
    average_quantity: Decimal = Field(default=Decimal('0'), decimal_places=2)


class GetStoreTransferStatisticsControllerReadDto(StoreTransferStatisticsReadBase):
    """Controller DTO for store transfer statistics"""
    pass


class GetStoreTransferStatisticsServiceReadDto(StoreTransferStatisticsReadBase):
    """Service DTO for store transfer statistics"""
    pass



