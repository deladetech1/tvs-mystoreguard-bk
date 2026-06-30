from typing import Optional, List
from pydantic import BaseModel, Field
from src.entities.estimate_templates.estimate_templates_base import (
    EstimateTemplateBase,
    LineItemDef,
    TemplateModifiers,
)


# =====================================================
# CREATE WRITE DTOs
# =====================================================

class CreateEstimateTemplateWriteBase(EstimateTemplateBase):
    """Create payload: full template definition."""
    pass


class CreateEstimateTemplateControllerWriteDto(CreateEstimateTemplateWriteBase):
    pass


class CreateEstimateTemplateServiceWriteDto(CreateEstimateTemplateWriteBase):
    pass


# =====================================================
# UPDATE WRITE DTOs
# =====================================================

class UpdateEstimateTemplateWriteBase(BaseModel):
    """Update payload. When `line_item_defs` or `modifiers` are provided they
    fully replace the stored definition (and bump the template version)."""
    name: Optional[str] = Field(None, min_length=1, max_length=255)
    domain: Optional[str] = Field(None, max_length=100)
    description: Optional[str] = Field(None, max_length=1000)
    is_active: Optional[bool] = None
    line_item_defs: Optional[List[LineItemDef]] = None
    modifiers: Optional[TemplateModifiers] = None


class UpdateEstimateTemplateControllerWriteDto(UpdateEstimateTemplateWriteBase):
    pass


class UpdateEstimateTemplateServiceWriteDto(UpdateEstimateTemplateWriteBase):
    pass


# =====================================================
# DELETE WRITE DTOs
# =====================================================

class DeleteEstimateTemplateWriteBase(BaseModel):
    template_id: str = Field(..., description="ID of the estimate template to delete")


class DeleteEstimateTemplateControllerWriteDto(DeleteEstimateTemplateWriteBase):
    pass


class DeleteEstimateTemplateServiceWriteDto(DeleteEstimateTemplateWriteBase):
    pass
