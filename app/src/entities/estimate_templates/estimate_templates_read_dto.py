from typing import Optional, List
from datetime import datetime
from pydantic import BaseModel, Field
from src.entities.estimate_templates.estimate_templates_base import (
    LineItemDef,
    TemplateModifiers,
)


# =====================================================
# ESTIMATE TEMPLATE READ DTOs
# =====================================================

class EstimateTemplateReadBase(BaseModel):
    """Base read DTO for an estimate template."""
    id: str
    tenant_id: str
    org_id: str
    bus_id: str
    name: str
    domain: Optional[str] = None
    description: Optional[str] = None
    version: int = 1
    line_item_defs: List[LineItemDef] = Field(default_factory=list)
    modifiers: TemplateModifiers = Field(default_factory=TemplateModifiers)
    delete_status: str
    is_active: bool
    cdate: Optional[str] = None
    ctime: Optional[str] = None
    cdatetime: Optional[datetime] = None
    created_by: Optional[str] = None
    updated_by: Optional[str] = None
    deleted_by: Optional[str] = None


class CreateEstimateTemplateControllerReadDto(EstimateTemplateReadBase):
    pass


class CreateEstimateTemplateServiceReadDto(EstimateTemplateReadBase):
    pass


class UpdateEstimateTemplateControllerReadDto(EstimateTemplateReadBase):
    pass


class UpdateEstimateTemplateServiceReadDto(EstimateTemplateReadBase):
    pass


class GetEstimateTemplateControllerReadDto(EstimateTemplateReadBase):
    pass


class GetEstimateTemplateServiceReadDto(EstimateTemplateReadBase):
    pass


class GetEstimateTemplateListControllerReadDto(EstimateTemplateReadBase):
    pass


class GetEstimateTemplateListServiceReadDto(EstimateTemplateReadBase):
    pass


class DeleteEstimateTemplateReadBase(BaseModel):
    template_id: str
    message: str


class DeleteEstimateTemplateControllerReadDto(DeleteEstimateTemplateReadBase):
    pass


class DeleteEstimateTemplateServiceReadDto(DeleteEstimateTemplateReadBase):
    pass
