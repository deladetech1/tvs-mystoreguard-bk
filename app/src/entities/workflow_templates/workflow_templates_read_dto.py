from typing import Optional, List, Dict
from datetime import datetime
from pydantic import BaseModel, Field
from src.entities.workflow_templates.workflow_templates_base import WorkflowTemplateBase


# =====================================================
# NESTED READ MODELS
# =====================================================

class StepTargetRead(BaseModel):
    id: str
    target_kind: str
    target_type: str
    target_id: str
    target_name: Optional[str] = Field(None, description="Resolved user or group name")


class WorkflowTemplateStepRead(BaseModel):
    id: str
    name: str
    description: Optional[str] = None
    display_order: int = 0
    default_location_id: Optional[str] = None
    depends_on: List[str] = Field(default_factory=list, description="ids of prerequisite steps")
    targets: List[StepTargetRead] = Field(default_factory=list)


# =====================================================
# TEMPLATE READ DTOs
# =====================================================

class WorkflowTemplateReadBase(WorkflowTemplateBase):
    id: str
    tenant_id: str
    org_id: str
    bus_id: str
    cdatetime: Optional[datetime] = None
    created_by: Optional[str] = None
    updated_by: Optional[str] = None
    deleted_by: Optional[str] = None
    steps: List[WorkflowTemplateStepRead] = Field(default_factory=list)


class CreateWorkflowTemplateControllerReadDto(WorkflowTemplateReadBase):
    pass


class CreateWorkflowTemplateServiceReadDto(WorkflowTemplateReadBase):
    pass


class UpdateWorkflowTemplateControllerReadDto(WorkflowTemplateReadBase):
    pass


class UpdateWorkflowTemplateServiceReadDto(WorkflowTemplateReadBase):
    pass


class GetWorkflowTemplateControllerReadDto(WorkflowTemplateReadBase):
    pass


class GetWorkflowTemplateServiceReadDto(WorkflowTemplateReadBase):
    pass


class GetWorkflowTemplatesControllerReadDto(WorkflowTemplateReadBase):
    pass


class GetWorkflowTemplatesServiceReadDto(WorkflowTemplateReadBase):
    pass


# =====================================================
# DELETE READ DTOs
# =====================================================

class DeleteWorkflowTemplateReadBase(BaseModel):
    template_id: str
    message: str


class DeleteWorkflowTemplateControllerReadDto(DeleteWorkflowTemplateReadBase):
    pass


class DeleteWorkflowTemplateServiceReadDto(DeleteWorkflowTemplateReadBase):
    pass


# =====================================================
# STATISTICS
# =====================================================

class TopUsedTemplateDto(BaseModel):
    template_id: str
    name: str
    jobs_created: int = 0


class WorkflowTemplateStatisticsReadBase(BaseModel):
    """Aggregate workflow-template statistics for the business."""
    total_templates: int = 0
    active: int = 0
    inactive: int = 0
    by_type: Dict[str, int] = Field(default_factory=dict, description="Template count per template_type")
    total_steps: int = 0
    avg_steps_per_template: float = Field(0, description="Average number of steps across templates")
    top_used_templates: List[TopUsedTemplateDto] = Field(
        default_factory=list, description="Templates ranked by jobs created from them")


class WorkflowTemplateStatisticsControllerReadDto(WorkflowTemplateStatisticsReadBase):
    pass


class WorkflowTemplateStatisticsServiceReadDto(WorkflowTemplateStatisticsReadBase):
    pass
