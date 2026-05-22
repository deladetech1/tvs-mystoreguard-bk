from typing import Optional, List
from datetime import datetime
from decimal import Decimal
from pydantic import BaseModel, Field


# =====================================================
# WAREHOUSE TRANSFER READ DTOs
# =====================================================

class WarehouseTransferItemRead(BaseModel):
    """A single product line within a warehouse transfer"""
    id: str
    product_id: str
    qty: int
    status: str
    product_name: Optional[str] = Field(None, description="Product name")


class WarehouseTransferReadBase(BaseModel):
    """Base read DTO for warehouse transfer"""
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
    items: List[WarehouseTransferItemRead] = Field(default_factory=list, description="Products being transferred")
    total_qty: int = Field(0, description="Sum of quantities across all items")
    source_location_name: Optional[str] = Field(None, description="Source location name")
    destination_location_name: Optional[str] = Field(None, description="Destination location name")
    created_by_name: Optional[str] = Field(None, description="Creator full name")
    approver_name: Optional[str] = Field(None, description="Approver full name")
    source_type: Optional[str] = Field(None, description="Source type (STORE or WAREHOUSE)")
    destination_type: Optional[str] = Field(None, description="Destination type (STORE or WAREHOUSE)")


class CreateWarehouseTransferControllerReadDto(WarehouseTransferReadBase):
    """Controller read DTO for creating a warehouse transfer"""
    pass


class CreateWarehouseTransferServiceReadDto(WarehouseTransferReadBase):
    """Service read DTO for creating a warehouse transfer"""
    pass


class GetWarehouseTransferControllerReadDto(WarehouseTransferReadBase):
    """Controller read DTO for getting a warehouse transfer"""
    pass


class GetWarehouseTransferServiceReadDto(WarehouseTransferReadBase):
    """Service read DTO for getting a warehouse transfer"""
    pass


class GetWarehouseTransfersControllerReadDto(WarehouseTransferReadBase):
    """Controller read DTO for listing warehouse transfers"""
    pass


class GetWarehouseTransfersServiceReadDto(WarehouseTransferReadBase):
    """Service read DTO for listing warehouse transfers"""
    pass


class ApproveWarehouseTransferControllerReadDto(WarehouseTransferReadBase):
    """Controller read DTO for approving/rejecting a warehouse transfer"""
    pass


class ApproveWarehouseTransferServiceReadDto(WarehouseTransferReadBase):
    """Service read DTO for approving/rejecting a warehouse transfer"""
    pass


class UpdateWarehouseTransferControllerReadDto(WarehouseTransferReadBase):
    """Controller read DTO for updating a warehouse transfer"""
    pass


class UpdateWarehouseTransferServiceReadDto(WarehouseTransferReadBase):
    """Service read DTO for updating a warehouse transfer"""
    pass


# =====================================================
# DELETE WAREHOUSE TRANSFER READ DTOs
# =====================================================

class DeleteWarehouseTransferReadBase(BaseModel):
    """Base read DTO for deleting a warehouse transfer"""
    success: bool = True
    message: str = "Warehouse transfer deleted successfully"


class DeleteWarehouseTransferControllerReadDto(DeleteWarehouseTransferReadBase):
    """Controller read DTO for deleting a warehouse transfer"""
    pass


class DeleteWarehouseTransferServiceReadDto(DeleteWarehouseTransferReadBase):
    """Service read DTO for deleting a warehouse transfer"""
    pass


# =====================================================
# WAREHOUSE TRANSFER STATISTICS READ DTOs
# =====================================================

class WarehouseTransferStatisticsReadBase(BaseModel):
    """Base read DTO for warehouse transfer statistics"""
    total_transfers: int = 0
    total_pending_approval: int = 0
    total_approved: int = 0
    total_rejected: int = 0
    total_completed: int = 0
    total_quantity: Decimal = Field(default=Decimal('0'), decimal_places=2)
    total_quantity_pending: Decimal = Field(default=Decimal('0'), decimal_places=2)
    average_quantity: Decimal = Field(default=Decimal('0'), decimal_places=2)


class GetWarehouseTransferStatisticsControllerReadDto(WarehouseTransferStatisticsReadBase):
    """Controller DTO for warehouse transfer statistics"""
    pass


class GetWarehouseTransferStatisticsServiceReadDto(WarehouseTransferStatisticsReadBase):
    """Service DTO for warehouse transfer statistics"""
    pass



