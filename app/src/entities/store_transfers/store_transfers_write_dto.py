from typing import Optional, Literal, List
from pydantic import BaseModel, Field
from src.entities.store_transfers.store_transfers_base import StoreTransferBase, StoreTransferItemInput


# =====================================================
# CREATE STORE TRANSFER WRITE DTOs
# =====================================================

class CreateStoreTransferControllerWriteDto(StoreTransferBase):
    """Controller DTO for creating a store transfer"""
    pass


class CreateStoreTransferServiceWriteDto(StoreTransferBase):
    """Service DTO for creating a store transfer"""
    pass


# =====================================================
# APPROVE/REJECT STORE TRANSFER WRITE DTOs
# =====================================================

class ApproveStoreTransferControllerWriteDto(BaseModel):
    """Controller DTO for approving/rejecting a store transfer"""
    transfer_id: str = Field(..., description="Transfer ID")
    action: str = Field(..., description="Action: 'APPROVE' or 'REJECT'")
    reason: Optional[str] = Field(None, description="Optional reason for rejection")


class ApproveStoreTransferServiceWriteDto(BaseModel):
    """Service DTO for approving/rejecting a store transfer"""
    transfer_id: str
    action: str
    reason: Optional[str] = None


# =====================================================
# UPDATE STORE TRANSFER WRITE DTOs
# =====================================================

class UpdateStoreTransferControllerWriteDto(BaseModel):
    """Controller DTO for updating a store transfer"""
    transfer_id: str = Field(..., description="Transfer ID")
    items: Optional[List[StoreTransferItemInput]] = Field(
        None, min_length=1, description="Replace the transfer's items with this list (optional)"
    )
    destination_type: Optional[Literal["STORE", "WAREHOUSE"]] = Field(None, description="Destination type")
    destination_id: Optional[str] = Field(None, description="Destination location ID")
    person_to_approve_id: Optional[str] = Field(None, description="User ID of person to approve the transfer")
    description: Optional[str] = Field(None, description="Optional description for the transfer")


class UpdateStoreTransferServiceWriteDto(BaseModel):
    """Service DTO for updating a store transfer"""
    transfer_id: str
    items: Optional[List[StoreTransferItemInput]] = None
    destination_type: Optional[Literal["STORE", "WAREHOUSE"]] = None
    destination_id: Optional[str] = None
    person_to_approve_id: Optional[str] = None
    description: Optional[str] = None


# =====================================================
# DELETE STORE TRANSFER WRITE DTOs
# =====================================================

class DeleteStoreTransferServiceWriteDto(BaseModel):
    """Service DTO for deleting a store transfer"""
    transfer_id: str


