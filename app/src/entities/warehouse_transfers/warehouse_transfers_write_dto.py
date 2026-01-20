from typing import Optional, Literal
from pydantic import BaseModel, Field
from src.entities.warehouse_transfers.warehouse_transfers_base import WarehouseTransferBase


# =====================================================
# CREATE WAREHOUSE TRANSFER WRITE DTOs
# =====================================================

class CreateWarehouseTransferControllerWriteDto(WarehouseTransferBase):
    """Controller DTO for creating a warehouse transfer"""
    pass


class CreateWarehouseTransferServiceWriteDto(WarehouseTransferBase):
    """Service DTO for creating a warehouse transfer"""
    pass


# =====================================================
# APPROVE/REJECT WAREHOUSE TRANSFER WRITE DTOs
# =====================================================

class ApproveWarehouseTransferControllerWriteDto(BaseModel):
    """Controller DTO for approving/rejecting a warehouse transfer"""
    transfer_id: str = Field(..., description="Transfer ID")
    action: str = Field(..., description="Action: 'APPROVE' or 'REJECT'")
    reason: Optional[str] = Field(None, description="Optional reason for rejection")


class ApproveWarehouseTransferServiceWriteDto(BaseModel):
    """Service DTO for approving/rejecting a warehouse transfer"""
    transfer_id: str
    action: str
    reason: Optional[str] = None


# =====================================================
# UPDATE WAREHOUSE TRANSFER WRITE DTOs
# =====================================================

class UpdateWarehouseTransferControllerWriteDto(BaseModel):
    """Controller DTO for updating a warehouse transfer"""
    transfer_id: str = Field(..., description="Transfer ID")
    qty: Optional[int] = Field(None, gt=0, description="Quantity to transfer")
    destination_type: Optional[Literal["STORE", "WAREHOUSE"]] = Field(None, description="Destination type")
    destination_id: Optional[str] = Field(None, description="Destination location ID")
    person_to_approve_id: Optional[str] = Field(None, description="User ID of person to approve the transfer")
    description: Optional[str] = Field(None, description="Optional description for the transfer")


class UpdateWarehouseTransferServiceWriteDto(BaseModel):
    """Service DTO for updating a warehouse transfer"""
    transfer_id: str
    qty: Optional[int] = None
    destination_type: Optional[Literal["STORE", "WAREHOUSE"]] = None
    destination_id: Optional[str] = None
    person_to_approve_id: Optional[str] = None
    description: Optional[str] = None


# =====================================================
# DELETE WAREHOUSE TRANSFER WRITE DTOs
# =====================================================

class DeleteWarehouseTransferServiceWriteDto(BaseModel):
    """Service DTO for deleting a warehouse transfer"""
    transfer_id: str


