from typing import Optional, List
from pydantic import BaseModel, Field
from src.entities.estimates.estimates_base import EstimateBase, EstimateLineItemInput, EstimateStatus


# =====================================================
# CREATE WRITE DTOs
# =====================================================

class CreateEstimateWriteBase(EstimateBase):
    items: List[EstimateLineItemInput] = Field(default_factory=list, description="Captured line items to price")


class CreateEstimateControllerWriteDto(CreateEstimateWriteBase):
    pass


class CreateEstimateServiceWriteDto(CreateEstimateWriteBase):
    pass


# =====================================================
# UPDATE WRITE DTOs (edit a draft: re-prices against the snapshot)
# =====================================================

class UpdateEstimateWriteBase(BaseModel):
    customer_id: Optional[str] = None
    title: Optional[str] = Field(None, max_length=255)
    notes: Optional[str] = Field(None, max_length=2000)
    # When provided, items fully replace the existing lines and the estimate is re-priced.
    items: Optional[List[EstimateLineItemInput]] = None


class UpdateEstimateControllerWriteDto(UpdateEstimateWriteBase):
    pass


class UpdateEstimateServiceWriteDto(UpdateEstimateWriteBase):
    pass


# =====================================================
# UPDATE STATUS WRITE DTOs
# =====================================================

class UpdateEstimateStatusWriteBase(BaseModel):
    status: EstimateStatus = Field(..., description="New status: DRAFT, SENT, ACCEPTED, REJECTED, EXPIRED, CONVERTED")


class UpdateEstimateStatusControllerWriteDto(UpdateEstimateStatusWriteBase):
    pass


class UpdateEstimateStatusServiceWriteDto(UpdateEstimateStatusWriteBase):
    pass


# =====================================================
# DELETE WRITE DTOs
# =====================================================

class DeleteEstimateWriteBase(BaseModel):
    estimate_id: str = Field(..., description="ID of the estimate to delete")


class DeleteEstimateControllerWriteDto(DeleteEstimateWriteBase):
    pass


class DeleteEstimateServiceWriteDto(DeleteEstimateWriteBase):
    pass
