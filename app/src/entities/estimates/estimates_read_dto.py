from typing import Optional, List, Any, Dict
from datetime import datetime, date
from pydantic import BaseModel, Field


# =====================================================
# ESTIMATE ITEM READ
# =====================================================

class EstimateItemReadBase(BaseModel):
    id: str
    estimate_id: str
    line_def_key: str
    name: Optional[str] = None
    label: Optional[str] = None
    quantity: float = 1.0
    field_values: Dict[str, Any] = Field(default_factory=dict)
    unit_amount: float = 0.0
    computed_amount: float = 0.0


# =====================================================
# ESTIMATE READ
# =====================================================

class EstimateReadBase(BaseModel):
    id: str
    tenant_id: str
    org_id: str
    bus_id: str
    loc_id: Optional[str] = None
    estimate_number: Optional[str] = None
    template_id: str
    template_version: int = 1
    customer_id: Optional[str] = None
    customer_name: Optional[str] = None
    title: Optional[str] = None
    notes: Optional[str] = None
    status: str = "DRAFT"
    currency: Optional[str] = None
    subtotal: float = 0.0
    markup_amount: float = 0.0
    discount_amount: float = 0.0
    tax_amount: float = 0.0
    grand_total: float = 0.0
    valid_until: Optional[date] = None
    items: List[EstimateItemReadBase] = Field(default_factory=list)
    delete_status: str = "NOT_DELETED"
    cdate: Optional[str] = None
    ctime: Optional[str] = None
    cdatetime: Optional[datetime] = None
    created_by: Optional[str] = None
    updated_by: Optional[str] = None
    deleted_by: Optional[str] = None


class CreateEstimateControllerReadDto(EstimateReadBase):
    pass


class CreateEstimateServiceReadDto(EstimateReadBase):
    pass


class UpdateEstimateControllerReadDto(EstimateReadBase):
    pass


class UpdateEstimateServiceReadDto(EstimateReadBase):
    pass


class GetEstimateControllerReadDto(EstimateReadBase):
    pass


class GetEstimateServiceReadDto(EstimateReadBase):
    pass


class GetEstimateListControllerReadDto(EstimateReadBase):
    pass


class GetEstimateListServiceReadDto(EstimateReadBase):
    pass


class UpdateEstimateStatusControllerReadDto(EstimateReadBase):
    pass


class UpdateEstimateStatusServiceReadDto(EstimateReadBase):
    pass


class DeleteEstimateReadBase(BaseModel):
    estimate_id: str
    message: str


class DeleteEstimateControllerReadDto(DeleteEstimateReadBase):
    pass


class DeleteEstimateServiceReadDto(DeleteEstimateReadBase):
    pass
