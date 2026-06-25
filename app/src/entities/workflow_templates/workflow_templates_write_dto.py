from typing import Optional, List
from pydantic import BaseModel, Field
from src.entities.workflow_templates.workflow_templates_base import (
    WorkflowTemplateBase,
    WorkflowType,
    StepInput,
)


# =====================================================
# CREATE WRITE DTOs
# =====================================================

class CreateWorkflowTemplateWriteBase(WorkflowTemplateBase):
    steps: List[StepInput] = Field(default_factory=list, description="Ordered steps that make up the workflow")


class CreateWorkflowTemplateControllerWriteDto(CreateWorkflowTemplateWriteBase):
    pass


class CreateWorkflowTemplateServiceWriteDto(CreateWorkflowTemplateWriteBase):
    pass


# =====================================================
# UPDATE WRITE DTOs
# =====================================================

class UpdateWorkflowTemplateWriteBase(BaseModel):
    name: Optional[str] = Field(None, min_length=1, max_length=255)
    template_type: Optional[WorkflowType] = None
    description: Optional[str] = None
    is_active: Optional[bool] = None
    # When provided, the template's steps/deps/targets are fully replaced.
    steps: Optional[List[StepInput]] = None


class UpdateWorkflowTemplateControllerWriteDto(UpdateWorkflowTemplateWriteBase):
    pass


class UpdateWorkflowTemplateServiceWriteDto(UpdateWorkflowTemplateWriteBase):
    pass


# =====================================================
# DELETE WRITE DTOs
# =====================================================

class DeleteWorkflowTemplateWriteBase(BaseModel):
    template_id: str


class DeleteWorkflowTemplateControllerWriteDto(DeleteWorkflowTemplateWriteBase):
    pass


class DeleteWorkflowTemplateServiceWriteDto(DeleteWorkflowTemplateWriteBase):
    pass
