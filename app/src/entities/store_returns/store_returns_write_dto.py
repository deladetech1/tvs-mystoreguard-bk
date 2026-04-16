from typing import Optional, List
from pydantic import BaseModel, Field
from src.entities.store_returns.store_returns_base import ReturnBase, ReturnItemBase


# =====================================================
# CREATE RETURN WRITE DTOs
# =====================================================

class CreateReturnWriteBase(ReturnBase):
    """Base write DTO for creating a return"""
    items: List[ReturnItemBase] = Field(..., min_length=1, description="List of items to return (at least one)")


class CreateReturnControllerWriteDto(CreateReturnWriteBase):
    """Controller DTO for creating a return"""
    pass


class CreateReturnServiceWriteDto(CreateReturnWriteBase):
    """Service DTO for creating a return"""
    pass


# =====================================================
# APPROVE RETURN WRITE DTOs
# =====================================================

class ApproveReturnWriteBase(BaseModel):
    """Base write DTO for approving a return"""
    return_id: str = Field(..., description="ID of the return to approve")
    notes: Optional[str] = Field(None, max_length=500, description="Approval notes")


class ApproveReturnControllerWriteDto(ApproveReturnWriteBase):
    """Controller DTO for approving a return"""
    pass


class ApproveReturnServiceWriteDto(ApproveReturnWriteBase):
    """Service DTO for approving a return"""
    pass


# =====================================================
# REJECT RETURN WRITE DTOs
# =====================================================

class RejectReturnWriteBase(BaseModel):
    """Base write DTO for rejecting a return"""
    return_id: str = Field(..., description="ID of the return to reject")
    rejection_reason: str = Field(..., min_length=1, max_length=500, description="Reason for rejecting the return")


class RejectReturnControllerWriteDto(RejectReturnWriteBase):
    """Controller DTO for rejecting a return"""
    pass


class RejectReturnServiceWriteDto(RejectReturnWriteBase):
    """Service DTO for rejecting a return"""
    pass


# =====================================================
# PROCESS RETURN WRITE DTOs
# =====================================================

class ProcessReturnWriteBase(BaseModel):
    """Base write DTO for processing a return (restock + refund)"""
    return_id: str = Field(..., description="ID of the return to process")
    notes: Optional[str] = Field(None, max_length=500, description="Processing notes")


class ProcessReturnControllerWriteDto(ProcessReturnWriteBase):
    """Controller DTO for processing a return"""
    pass


class ProcessReturnServiceWriteDto(ProcessReturnWriteBase):
    """Service DTO for processing a return"""
    pass
